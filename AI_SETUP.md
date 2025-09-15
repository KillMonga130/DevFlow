# DevFlow AI Setup Guide

## 🤖 GPT-OSS + Ollama Integration

DevFlow leverages GPT-OSS models through Ollama for real-time AI features. Follow this guide to unlock the full AI-powered experience.

## Prerequisites

### 1. Install Ollama
```bash
# Windows (PowerShell)
winget install Ollama.Ollama

# Or download from: https://ollama.ai/download
```

### 2. Pull GPT-OSS Model
```bash
# Pull the GPT-OSS model (choose based on your hardware)
ollama pull gpt-oss:20b    # For most systems
# or
ollama pull gpt-oss:120b   # For high-end systems with 64GB+ RAM
```

### 3. Start Ollama Service
```bash
# Start Ollama (usually runs automatically after install)
ollama serve
```

## Verify Installation

### Check Model Availability
```bash
ollama list
# Should show gpt-oss:20b or gpt-oss:120b
```

### Test API Connection
```bash
curl http://localhost:11434/api/tags
# Should return JSON with available models
```

## DevFlow AI Features

Once Ollama is running with GPT-OSS, DevFlow unlocks these AI-powered features:

### 🎯 **AI Exercise Generator**
- **Real-time code generation** with educational flaws
- **Customizable scenarios** (authentication, data processing, etc.)
- **Multi-language support** (JavaScript, Python, TypeScript, Java, C#)
- **Difficulty adaptation** based on user skill level

### 🔍 **AI Code Analyzer**  
- **Instant issue detection** in user-submitted code
- **Comprehensive analysis** covering security, performance, logic, style
- **Detailed explanations** with improvement suggestions
- **Learning-focused feedback** tailored for skill development

### 💬 **Personalized AI Feedback**
- **Context-aware responses** based on user performance
- **Encouraging guidance** that adapts to learning progress
- **Specific improvement tips** for weak skill areas
- **Motivational milestone recognition**

## Configuration

### Update Model Selection
Edit `server/ollama-service.js` to change the model:
```javascript
this.model = 'gpt-oss:20b'; // or 'gpt-oss:20b'
```

### Adjust AI Parameters
Fine-tune AI behavior in the service methods:
```javascript
options: {
  temperature: 0.7,  // Creativity (0.0-1.0)
  top_p: 0.9,       // Diversity (0.0-1.0)
  max_tokens: 1000  // Response length
}
```

## Troubleshooting

### "AI features disabled" message
1. **Check Ollama is running**: `ollama list`
2. **Verify model is pulled**: Should see gpt-oss in the list
3. **Test API**: `curl http://localhost:11434/api/tags`
4. **Restart DevFlow backend**: The server checks AI availability on startup

### Slow AI responses
1. **Use smaller model**: Switch to gpt-oss:20b if using 120b
2. **Reduce max_tokens**: Lower the token limit in ollama-service.js
3. **Check system resources**: Ensure adequate RAM and CPU

### Connection errors
1. **Firewall**: Ensure port 11434 is accessible
2. **Ollama service**: Restart with `ollama serve`
3. **Model corruption**: Re-pull the model with `ollama pull gpt-oss:20b`

## Performance Optimization

### Hardware Recommendations
- **gpt-oss:20b**: 16GB+ RAM, modern CPU
- **gpt-oss:120b**: 64GB+ RAM, high-end CPU/GPU

### Speed Optimization
- **Lower temperature**: Faster, more deterministic responses
- **Reduce max_tokens**: Shorter responses, faster generation
- **Use SSD storage**: Faster model loading

## Hackathon Demo Tips

### Showcase AI Features
1. **Start with AI Generator**: Show real-time code creation
2. **Demonstrate Analysis**: Upload flawed code for instant feedback
3. **Highlight Personalization**: Show how feedback adapts to user
4. **Emphasize Education**: Focus on learning value, not just automation

### Fallback for Demo
If AI isn't available during demo:
- DevFlow works fully without AI using pre-generated exercises
- Mention AI capabilities and show the interface
- Emphasize the dual hackathon approach (Kiro + GPT-OSS)

## Impact Statement

**For Humanity**: DevFlow democratizes code review education, making this critical skill accessible to developers worldwide, regardless of their access to senior mentors.

**Technical Innovation**: Combines development-time AI (Kiro) with runtime AI (GPT-OSS) to create a comprehensive learning platform that adapts to each user's needs.

**Scalable Solution**: AI-generated content ensures unlimited, fresh exercises while personalized feedback accelerates skill development for developers at any level.