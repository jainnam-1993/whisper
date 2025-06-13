#!/usr/bin/env python3
"""
AWS Transcribe Streaming Speech-to-Text Test
Compares streaming transcription performance with local Whisper model.
"""

import asyncio
import json
import time
import wave
import pyaudio
import threading
from datetime import datetime
import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import whisper
import numpy as np

class StreamingTranscriptionHandler(TranscriptResultStreamHandler):
    """Handler for AWS Transcribe streaming results"""
    
    def __init__(self):
        # No parameters needed - stream is passed to handle_transcript_event_stream method
        pass
        self.transcript_parts = []
        self.start_time = None
        self.first_result_time = None
        self.final_transcript = ""
        
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        """Handle incoming transcript events"""
        if self.start_time is None:
            self.start_time = time.time()
            
        results = transcript_event.transcript.results
        for result in results:
            if self.first_result_time is None:
                self.first_result_time = time.time()
                
            for alt in result.alternatives:
                transcript = alt.transcript
                if result.is_partial:
                    print(f"[PARTIAL] {transcript}")
                else:
                    print(f"[FINAL] {transcript}")
                    self.transcript_parts.append(transcript)
                    self.final_transcript = " ".join(self.transcript_parts)

    async def handle_transcript_event_stream(self, transcript_result_stream):
        """Handle the transcript event stream"""
        try:
            async for transcript_event in transcript_result_stream:
                await self.handle_transcript_event(transcript_event)
        except Exception as e:
            print(f"Error handling transcript stream: {e}")
class AudioStreamer:
    """Handles audio streaming for real-time transcription"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False
        
    def start_microphone_stream(self):
        """Start streaming from microphone"""
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        self.is_streaming = True
        return self._microphone_generator()
        
    def stream_from_file(self, audio_file_path):
        """Stream audio from file to simulate real-time input"""
        with wave.open(audio_file_path, 'rb') as wav_file:
            # Ensure audio is in correct format
            if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
                raise ValueError("Audio file must be mono, 16-bit PCM")
                
            sample_rate = wav_file.getframerate()
            if sample_rate != self.sample_rate:
                print(f"Warning: File sample rate {sample_rate} != {self.sample_rate}")
                
            return self._file_generator(wav_file)
    
    def _microphone_generator(self):
        """Generate audio chunks from microphone"""
        while self.is_streaming:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                yield data
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
                
    def _file_generator(self, wav_file):
        """Generate audio chunks from file with realistic timing"""
        chunk_duration = self.chunk_size / self.sample_rate
        
        while True:
            data = wav_file.readframes(self.chunk_size)
            if not data:
                break
                
            yield data
            # Simulate real-time by waiting
            time.sleep(chunk_duration * 0.8)  # Slightly faster than real-time
            
    def stop(self):
        """Stop audio streaming"""
        self.is_streaming = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

class StreamingTranscriptionTester:
    """Main class for testing streaming transcription performance"""
    
    def __init__(self):
        self.whisper_model = None
        self.transcribe_client = None
        self.original_env = None
        
    def load_whisper_model(self, model_name="medium"):
        """Load Whisper model for comparison"""
        print(f"Loading Whisper {model_name} model...")
        start_time = time.time()
        self.whisper_model = whisper.load_model(model_name)
        load_time = time.time() - start_time
        print(f"Whisper model loaded in {load_time:.2f}s")
        return load_time
        
    def setup_aws_transcribe(self, region="us-west-2"):
        """Setup AWS Transcribe streaming client"""
        try:
            import boto3
            import os
            
            # Get AWS credentials using boto3
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                raise Exception("No AWS credentials found. Please configure your credentials.")
            
            print("AWS credentials loaded successfully")
            
            # Temporarily set environment variables for the amazon-transcribe library
            # Store original values to restore later
            original_env = {}
            env_keys = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION']
            
            for key in env_keys:
                if key in os.environ:
                    original_env[key] = os.environ[key]
            
            os.environ['AWS_ACCESS_KEY_ID'] = credentials.access_key
            os.environ['AWS_SECRET_ACCESS_KEY'] = credentials.secret_key
            if credentials.token:
                os.environ['AWS_SESSION_TOKEN'] = credentials.token
            os.environ['AWS_DEFAULT_REGION'] = region
            
            # Create TranscribeStreamingClient
            self.transcribe_client = TranscribeStreamingClient(region=region)
            
            # Store original environment for cleanup
            self.original_env = original_env
            
            print(f"AWS Transcribe Streaming client initialized for region: {region}")
            return True
        except Exception as e:
            print(f"Failed to initialize AWS Transcribe client: {e}")
            return False
    
    def cleanup_aws_credentials(self):
        """Clean up AWS credentials from environment variables"""
        if self.original_env is not None:
            try:
                # Clear AWS credentials from environment
                for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN']:
                    if key in os.environ:
                        del os.environ[key]
                
                # Restore original environment
                for key, value in self.original_env.items():
                    os.environ[key] = value
                    
                print("AWS credentials cleaned up from environment")
            except Exception as e:
                print(f"Warning: Could not clean up AWS credentials: {e}")
                
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.cleanup_aws_credentials()
            
    async def test_streaming_transcription(self, audio_source="microphone", duration=10, audio_file=None):
        """Test AWS Transcribe streaming performance"""
        if not self.transcribe_client:
            print("AWS Transcribe client not initialized")
            return None
            
        print(f"\n{'='*50}")
        print("AWS TRANSCRIBE STREAMING TEST")
        print(f"{'='*50}")
        
        handler = StreamingTranscriptionHandler()
        audio_streamer = AudioStreamer()
        
        try:
            # Setup audio stream
            if audio_source == "microphone":
                print(f"Starting microphone recording for {duration} seconds...")
                print("Speak now!")
                audio_stream = audio_streamer.start_microphone_stream()
            elif audio_source == "file" and audio_file:
                print(f"Streaming from file: {audio_file}")
                audio_stream = audio_streamer.stream_from_file(audio_file)
            else:
                raise ValueError("Invalid audio source or missing file")
                
            # Start streaming transcription with minimal required parameters
            stream = await self.transcribe_client.start_stream_transcription(
                language_code="en-US",
                media_sample_rate_hz=16000,
                media_encoding="pcm"
            )
            
            # Start handling results
            handler_task = asyncio.create_task(handler.handle_transcript_event_stream(stream.output_stream))
            
            # Stream audio data
            start_time = time.time()
            audio_duration = 0
            
            if audio_source == "microphone":
                # Stream for specified duration
                end_time = start_time + duration
                async for chunk in self._async_audio_generator(audio_stream):
                    if time.time() > end_time:
                        break
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    audio_duration = time.time() - start_time
            else:
                # Stream entire file
                async for chunk in self._async_audio_generator(audio_stream):
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    audio_duration = time.time() - start_time
                    
            # End the stream
            await stream.input_stream.end_stream()
            await handler_task
            
            # Calculate metrics
            total_time = time.time() - start_time
            first_result_latency = (handler.first_result_time - handler.start_time) if handler.first_result_time and handler.start_time else None
            
            results = {
                'transcript': handler.final_transcript,
                'audio_duration': audio_duration,
                'total_processing_time': total_time,
                'first_result_latency': first_result_latency,
                'real_time_factor': total_time / audio_duration if audio_duration > 0 else None,
                'streaming': True
            }
            
            print(f"\nSTREAMING RESULTS:")
            print(f"Transcript: {results['transcript']}")
            print(f"Audio Duration: {results['audio_duration']:.2f}s")
            print(f"Total Processing Time: {results['total_processing_time']:.2f}s")
            if first_result_latency:
                print(f"First Result Latency: {first_result_latency:.2f}s")
            if results['real_time_factor']:
                print(f"Real-time Factor: {results['real_time_factor']:.2f}x")
                
            return results
            
        except Exception as e:
            print(f"Streaming transcription error: {e}")
            return None
        finally:
            audio_streamer.stop()
            
    async def _async_audio_generator(self, sync_generator):
        """Convert synchronous audio generator to async"""
        loop = asyncio.get_event_loop()
        
        def get_next_chunk():
            try:
                return next(sync_generator)
            except StopIteration:
                return None
                
        while True:
            chunk = await loop.run_in_executor(None, get_next_chunk)
            if chunk is None:
                break
            yield chunk
            
    def test_whisper_comparison(self, audio_file):
        """Test Whisper model for comparison"""
        if not self.whisper_model:
            print("Whisper model not loaded")
            return None
            
        print(f"\n{'='*50}")
        print("WHISPER COMPARISON TEST")
        print(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = self.whisper_model.transcribe(audio_file)
            end_time = time.time()
            
            # Get audio duration
            import librosa
            audio_data, sr = librosa.load(audio_file, sr=16000)
            audio_duration = len(audio_data) / sr
            
            processing_time = end_time - start_time
            real_time_factor = processing_time / audio_duration
            
            results = {
                'transcript': result['text'].strip(),
                'audio_duration': audio_duration,
                'total_processing_time': processing_time,
                'real_time_factor': real_time_factor,
                'streaming': False
            }
            
            print(f"Transcript: {results['transcript']}")
            print(f"Audio Duration: {results['audio_duration']:.2f}s")
            print(f"Processing Time: {results['total_processing_time']:.2f}s")
            print(f"Real-time Factor: {results['real_time_factor']:.2f}x")
            
            return results
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return None

def print_comparison(streaming_results, whisper_results):
    """Print detailed comparison between streaming and batch processing"""
    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    
    if streaming_results and whisper_results:
        print(f"{'Metric':<25} {'Streaming':<15} {'Whisper':<15} {'Winner'}")
        print(f"{'-'*60}")
        
        # Real-time factor comparison
        if streaming_results.get('real_time_factor') and whisper_results.get('real_time_factor'):
            streaming_rtf = streaming_results['real_time_factor']
            whisper_rtf = whisper_results['real_time_factor']
            winner = "Streaming" if streaming_rtf < whisper_rtf else "Whisper"
            print(f"{'Real-time Factor':<25} {streaming_rtf:<15.2f} {whisper_rtf:<15.2f} {winner}")
            
        # First result latency (streaming advantage)
        if streaming_results.get('first_result_latency'):
            latency = streaming_results['first_result_latency']
            print(f"{'First Result Latency':<25} {latency:<15.2f} {'N/A':<15} {'Streaming'}")
            
        # Transcript comparison
        streaming_text = streaming_results.get('transcript', '').strip()
        whisper_text = whisper_results.get('transcript', '').strip()
        
        print(f"\nTranscript Comparison:")
        print(f"Streaming: {streaming_text}")
        print(f"Whisper:   {whisper_text}")
        
        # Simple accuracy check
        if streaming_text and whisper_text:
            similarity = len(set(streaming_text.lower().split()) & set(whisper_text.lower().split()))
            total_words = len(set(streaming_text.lower().split()) | set(whisper_text.lower().split()))
            if total_words > 0:
                similarity_pct = (similarity / total_words) * 100
                print(f"Word Similarity: {similarity_pct:.1f}%")

async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AWS Transcribe Streaming vs Whisper")
    parser.add_argument("--audio-file", help="Audio file to test (optional)")
    parser.add_argument("--duration", type=int, default=10, help="Recording duration for microphone test")
    parser.add_argument("--whisper-model", default="medium", help="Whisper model size")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--source", choices=["microphone", "file"], default="microphone", help="Audio source")
    
    args = parser.parse_args()
    
    tester = StreamingTranscriptionTester()
    
    # Load Whisper model
    whisper_load_time = tester.load_whisper_model(args.whisper_model)
    
    # Setup AWS Transcribe
    if not tester.setup_aws_transcribe(args.region):
        print("Failed to setup AWS Transcribe. Check your AWS credentials.")
        return
        
    # Test streaming transcription
    if args.source == "file" and not args.audio_file:
        print("Error: --audio-file required when using file source")
        return
        
    streaming_results = await tester.test_streaming_transcription(
        audio_source=args.source,
        duration=args.duration,
        audio_file=args.audio_file
    )
    
    # Test Whisper for comparison (only if we have an audio file)
    whisper_results = None
    if args.audio_file:
        whisper_results = tester.test_whisper_comparison(args.audio_file)
    elif args.source == "microphone":
        print("\nNote: Whisper comparison requires an audio file. Use --audio-file option.")
        
    # Print comparison
    if streaming_results:
        print_comparison(streaming_results, whisper_results)
        
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())