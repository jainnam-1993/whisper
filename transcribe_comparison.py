#!/usr/bin/env python3
"""
AWS Transcribe vs Local Whisper Performance Comparison Script

Usage: python transcribe_comparison.py <audio_file>

This script compares the performance of local Whisper medium model
against AWS Transcribe service using the same audio file.
"""

import argparse
import time
import os
import sys
import uuid
import json
from pathlib import Path

import numpy as np
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from whisper import load_model
import librosa


class WhisperTranscriber:
    """Local Whisper transcription using medium model"""
    
    def __init__(self):
        self.model = None
        self.model_load_time = 0
    
    def load_model_if_needed(self):
        """Load Whisper model (one-time cost)"""
        if self.model is None:
            print("Loading Whisper medium model...")
            start_time = time.time()
            self.model = load_model("medium")
            self.model_load_time = time.time() - start_time
            print(f"Model loaded in {self.model_load_time:.2f}s")
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using Whisper"""
        self.load_model_if_needed()
        
        # Load audio file (convert to format expected by Whisper)
        print("Loading audio file for Whisper...")
        audio_data, sample_rate = librosa.load(audio_file_path, sr=16000, mono=True)
        
        # Measure transcription time only (not model loading)
        print("Transcribing with Whisper...")
        start_time = time.time()
        result = self.model.transcribe(audio_data)
        transcription_time = time.time() - start_time
        
        return {
            'text': result['text'].strip(),
            'transcription_time': transcription_time,
            'model_load_time': self.model_load_time,
            'language': result.get('language', 'unknown')
        }


class AWSTranscriber:
    """AWS Transcribe service integration"""
    
    def __init__(self, region='us-west-2'):
        self.region = region
        self.s3_client = None
        self.transcribe_client = None
        self.bucket_name = f"whisper-comparison-{uuid.uuid4().hex[:8]}"
    
    def _init_clients(self):
        """Initialize AWS clients"""
        if self.s3_client is None:
            try:
                self.s3_client = boto3.client('s3', region_name=self.region)
                self.transcribe_client = boto3.client('transcribe', region_name=self.region)
            except NoCredentialsError:
                raise Exception("AWS credentials not configured. Please run 'aws configure' or set environment variables.")
    
    def _create_temp_bucket(self):
        """Create temporary S3 bucket for audio upload"""
        try:
            if self.region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            print(f"Created temporary S3 bucket: {self.bucket_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyExists':
                # Use existing bucket
                pass
            else:
                raise
    
    def _cleanup_bucket(self):
        """Clean up temporary S3 bucket and objects"""
        try:
            # Delete all objects in bucket
            objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            if 'Contents' in objects:
                delete_objects = [{'Key': obj['Key']} for obj in objects['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_objects}
                )
            
            # Delete bucket
            self.s3_client.delete_bucket(Bucket=self.bucket_name)
            print(f"Cleaned up S3 bucket: {self.bucket_name}")
        except ClientError as e:
            print(f"Warning: Could not clean up S3 bucket: {e}")
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using AWS Transcribe"""
        self._init_clients()
        
        total_start_time = time.time()
        
        try:
            # Create temporary bucket
            self._create_temp_bucket()
            
            # Upload audio file to S3
            print("Uploading audio file to S3...")
            upload_start = time.time()
            audio_filename = Path(audio_file_path).name
            s3_key = f"audio/{uuid.uuid4().hex}-{audio_filename}"
            
            self.s3_client.upload_file(audio_file_path, self.bucket_name, s3_key)
            upload_time = time.time() - upload_start
            
            # Start transcription job
            print("Starting AWS Transcribe job...")
            job_name = f"whisper-comparison-{uuid.uuid4().hex[:8]}"
            job_uri = f"s3://{self.bucket_name}/{s3_key}"
            
            job_start = time.time()
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                Media={'MediaFileUri': job_uri},
                MediaFormat=self._get_media_format(audio_file_path),
                LanguageCode='en-US'  # Default to English
            )
            
            # Wait for job completion
            print("Waiting for transcription to complete...")
            while True:
                response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    break
                elif status == 'FAILED':
                    failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise Exception(f"AWS Transcribe job failed: {failure_reason}")
                
                time.sleep(2)  # Poll every 2 seconds
            
            job_time = time.time() - job_start
            
            # Get transcription results
            print("Retrieving transcription results...")
            result_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
            # Download transcript
            import urllib.request
            with urllib.request.urlopen(result_uri) as response_data:
                transcript_json = json.loads(response_data.read().decode())
            
            total_time = time.time() - total_start_time
            
            # Extract transcript text
            transcript_text = transcript_json['results']['transcripts'][0]['transcript']
            
            return {
                'text': transcript_text.strip(),
                'total_time': total_time,
                'upload_time': upload_time,
                'job_time': job_time,
                'job_name': job_name
            }
            
        finally:
            # Always clean up
            self._cleanup_bucket()
    
    def _get_media_format(self, audio_file_path):
        """Determine media format from file extension"""
        ext = Path(audio_file_path).suffix.lower()
        format_map = {
            '.wav': 'wav',
            '.mp3': 'mp3',
            '.mp4': 'mp4',
            '.m4a': 'mp4',
            '.flac': 'flac',
            '.ogg': 'ogg'
        }
        return format_map.get(ext, 'wav')  # Default to wav


def format_time(seconds):
    """Format time in a readable way"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def get_audio_duration(audio_file_path):
    """Get audio file duration"""
    try:
        audio_data, sample_rate = librosa.load(audio_file_path, sr=None)
        duration = len(audio_data) / sample_rate
        return duration
    except Exception as e:
        print(f"Warning: Could not determine audio duration: {e}")
        return None


def compare_transcriptions(audio_file_path):
    """Compare Whisper and AWS Transcribe performance"""
    
    if not os.path.exists(audio_file_path):
        print(f"Error: Audio file not found: {audio_file_path}")
        return
    
    print(f"🎵 Audio file: {audio_file_path}")
    
    # Get audio duration
    duration = get_audio_duration(audio_file_path)
    if duration:
        print(f"📏 Duration: {format_time(duration)}")
    
    print("\n" + "="*60)
    print("🔄 PERFORMANCE COMPARISON: AWS Transcribe vs Local Whisper")
    print("="*60)
    
    # Test local Whisper
    print("\n🤖 LOCAL WHISPER TRANSCRIPTION")
    print("-" * 40)
    
    whisper_transcriber = WhisperTranscriber()
    try:
        whisper_start = time.time()
        whisper_result = whisper_transcriber.transcribe_audio(audio_file_path)
        whisper_total = time.time() - whisper_start
        
        print(f"✅ Whisper completed successfully")
        print(f"📝 Text: {whisper_result['text']}")
        print(f"⏱️  Transcription time: {format_time(whisper_result['transcription_time'])}")
        print(f"🔄 Model load time: {format_time(whisper_result['model_load_time'])}")
        print(f"⏰ Total time: {format_time(whisper_total)}")
        if duration:
            speed_factor = duration / whisper_result['transcription_time']
            print(f"🚀 Speed: {speed_factor:.1f}x real-time")
        
    except Exception as e:
        print(f"❌ Whisper failed: {e}")
        whisper_result = None
    
    # Test AWS Transcribe
    print("\n☁️  AWS TRANSCRIBE")
    print("-" * 40)
    
    aws_transcriber = AWSTranscriber()
    try:
        aws_result = aws_transcriber.transcribe_audio(audio_file_path)
        
        print(f"✅ AWS Transcribe completed successfully")
        print(f"📝 Text: {aws_result['text']}")
        print(f"📤 Upload time: {format_time(aws_result['upload_time'])}")
        print(f"⏱️  Processing time: {format_time(aws_result['job_time'])}")
        print(f"⏰ Total time: {format_time(aws_result['total_time'])}")
        if duration:
            speed_factor = duration / aws_result['total_time']
            print(f"🚀 Speed: {speed_factor:.1f}x real-time")
        
    except Exception as e:
        print(f"❌ AWS Transcribe failed: {e}")
        aws_result = None
    
    # Comparison summary
    print("\n📊 COMPARISON SUMMARY")
    print("-" * 40)
    
    if whisper_result and aws_result:
        whisper_time = whisper_result['transcription_time']
        aws_time = aws_result['total_time']
        
        if whisper_time < aws_time:
            winner = "Whisper"
            time_diff = aws_time - whisper_time
            print(f"🏆 Winner: {winner} (faster by {format_time(time_diff)})")
        else:
            winner = "AWS Transcribe"
            time_diff = whisper_time - aws_time
            print(f"🏆 Winner: {winner} (faster by {format_time(time_diff)})")
        
        # Text comparison
        if whisper_result['text'].lower() == aws_result['text'].lower():
            print("📝 Transcription: Identical results")
        else:
            print("📝 Transcription: Different results (see above)")
            
        # Speed comparison
        if duration:
            print(f"🚀 Whisper speed: {duration/whisper_time:.1f}x real-time")
            print(f"🚀 AWS speed: {duration/aws_time:.1f}x real-time")
    
    elif whisper_result:
        print("🏆 Only Whisper completed successfully")
    elif aws_result:
        print("🏆 Only AWS Transcribe completed successfully")
    else:
        print("❌ Both methods failed")
    
    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Compare AWS Transcribe vs Local Whisper performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcribe_comparison.py audio.wav
  python transcribe_comparison.py recording.mp3
  
Requirements:
  - AWS CLI configured (aws configure)
  - Audio file in supported format (wav, mp3, mp4, m4a, flac, ogg)
  - Internet connection for AWS Transcribe
        """
    )
    
    parser.add_argument('audio_file', help='Path to audio file to transcribe')
    parser.add_argument('--region', default='us-west-2', 
                       help='AWS region for Transcribe service (default: us-west-2)')
    
    args = parser.parse_args()
    
    # Validate audio file
    if not os.path.exists(args.audio_file):
        print(f"Error: Audio file not found: {args.audio_file}")
        sys.exit(1)
    
    # Run comparison
    try:
        compare_transcriptions(args.audio_file)
    except KeyboardInterrupt:
        print("\n\n⏹️  Comparison interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()