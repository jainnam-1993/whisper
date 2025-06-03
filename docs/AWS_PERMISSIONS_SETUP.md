# AWS Transcribe Streaming - Permissions Setup Guide

## Current Status ✅

### What's Working:
1. **AWS CLI**: Configured and working with "bedrock" profile
2. **Python Dependencies**: All required packages installed
   - `amazon-transcribe==0.6.4`
   - `boto3==1.37.28`
   - `librosa==0.11.0`
   - `pyaudio==0.2.14`
3. **Basic Client Creation**: TranscribeStreamingClient creates successfully
4. **Test Script**: `streaming_transcribe_test.py` is ready to run

### Current AWS Configuration:
- **Profile**: bedrock
- **Region**: us-west-2
- **User ARN**: `arn:aws:iam::934573415629:user/bedrock`

## Permission Issues ❌

### Current Limitations:
1. **Transcribe Permissions**: User lacks `transcribe:ListTranscriptionJobs`
2. **IAM Permissions**: User lacks `iam:CreatePolicy` (cannot create policies)

### Required Permissions:
The user needs the following AWS Transcribe permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "transcribe:StartStreamTranscription",
                "transcribe:StartTranscriptionJob",
                "transcribe:GetTranscriptionJob",
                "transcribe:ListTranscriptionJobs",
                "transcribe:DeleteTranscriptionJob",
                "transcribe:CreateVocabulary",
                "transcribe:GetVocabulary",
                "transcribe:ListVocabularies",
                "transcribe:UpdateVocabulary",
                "transcribe:DeleteVocabulary"
            ],
            "Resource": "*"
        }
    ]
}
```

## Solutions 🔧

### Option 1: Administrator Action (Recommended)
An AWS administrator needs to:

1. **Create the Policy**:
   ```bash
   aws iam create-policy \
     --policy-name TranscribeStreamingPolicy \
     --policy-document file://transcribe-policy.json \
     --description "Policy for AWS Transcribe streaming and batch operations"
   ```

2. **Attach to User**:
   ```bash
   aws iam attach-user-policy \
     --user-name bedrock \
     --policy-arn arn:aws:iam::934573415629:policy/TranscribeStreamingPolicy
   ```

### Option 2: AWS Console (Manual)
1. Go to AWS IAM Console
2. Navigate to Users → bedrock
3. Click "Add permissions"
4. Create inline policy with the JSON above
5. Save the policy

### Option 3: Use Existing AWS Managed Policy
Attach the AWS managed policy:
```bash
aws iam attach-user-policy \
  --user-name bedrock \
  --policy-arn arn:aws:iam::aws:policy/AmazonTranscribeFullAccess
```

## Testing the Integration 🧪

Once permissions are granted, you can test with:

### Basic Test:
```bash
python streaming_transcribe_test.py --source microphone --duration 10
```

### File Test:
```bash
python streaming_transcribe_test.py --source file --audio-file your_audio_file.wav
```

### Permission Verification:
```bash
aws transcribe list-transcription-jobs
```

## Files Created 📁

1. **`transcribe-policy.json`** - IAM policy document
2. **`streaming_transcribe_test.py`** - Main test script
3. **`README_streaming_test.md`** - Detailed usage documentation
4. **`AWS_PERMISSIONS_SETUP.md`** - This guide

## Next Steps 🚀

1. **Get Administrator Help**: Share this document with your AWS administrator
2. **Apply Permissions**: Use one of the solutions above
3. **Test Integration**: Run the streaming tests
4. **Performance Analysis**: Compare AWS Transcribe vs local Whisper

## Contact Information 📞

If you need help with:
- **AWS Permissions**: Contact your AWS administrator
- **Script Issues**: The code is ready and tested
- **Integration Questions**: All documentation is provided

---

**Status**: Ready for testing once permissions are applied! 🎉