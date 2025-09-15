# DevFlow MVP 🚀

AI-Powered Code Review Education Platform - Minimal Viable Product

## What is DevFlow MVP?

A simplified version of DevFlow that demonstrates the core concept: AI-generated code exercises with instant feedback for learning code review skills.

## Features

✅ **AI-Generated Exercises** - Creates realistic JavaScript code with intentional bugs  
✅ **Interactive Code Review** - Click on lines to mark issues  
✅ **Instant Feedback** - See what you found vs. what you missed  
✅ **Progress Tracking** - Basic stats and scoring  
✅ **Smart Fallbacks** - Works with or without AI (demo mode)  

## Quick Start

1. **Setup** (one time):
   ```bash
   setup.bat
   ```

2. **Start the application**:
   ```bash
   start.bat
   ```

3. **Access the app**:
   - Open http://localhost:3000
   - Click "Start Code Review"
   - Find issues in the code
   - Get instant feedback!

## Requirements

- Node.js (v16 or higher)
- npm
- Optional: Ollama with gpt-oss model for AI features

## How It Works

1. **Generate Exercise**: AI creates JavaScript code with 2-3 intentional bugs
2. **Review Code**: Click on lines where you find issues, specify the type
3. **Get Feedback**: See your score and what you missed
4. **Improve**: Try more exercises to build your skills

## AI Integration

The MVP works in two modes:

### AI Mode (Ollama Available)
- Generates unique code exercises using gpt-oss model
- Provides varied, realistic scenarios
- Adapts to different types of issues

### Demo Mode (Fallback)
- Uses pre-built exercise templates
- Smart analysis based on code patterns
- Fully functional without AI dependency

## Project Structure

```
devflow-mvp/
├── server/           # Express.js backend
│   ├── server.js     # Main server file
│   └── ollama-service.js # AI integration
├── client/           # React frontend
│   ├── src/
│   │   ├── App.js    # Main React component
│   │   └── App.css   # Styling
│   └── public/
└── setup.bat         # Setup script
```

## API Endpoints

- `POST /api/exercise/generate` - Generate new exercise
- `POST /api/exercise/:id/submit` - Submit review for scoring
- `GET /api/stats` - Get user statistics
- `GET /api/health` - Check system status

## Development

### Start in development mode:
```bash
# Start both server and client with hot reload
npm run dev

# Or start separately:
cd server && npm run dev    # Server on :3001
cd client && npm start      # Client on :3000
```

### Database
- Uses SQLite (devflow-mvp.db)
- Auto-creates tables on first run
- Stores exercises and user attempts

## Extending the MVP

This MVP provides the foundation for:
- User authentication and profiles
- Multiple programming languages
- Advanced gamification features
- Real-time collaboration
- Detailed analytics and insights

## Troubleshooting

### AI Not Working?
- Check if Ollama is running: `ollama serve`
- Verify model is available: `ollama list`
- MVP works fine in demo mode without AI

### Port Conflicts?
- Server uses port 3001
- Client uses port 3000
- Change ports in package.json if needed

### Dependencies Issues?
- Delete node_modules folders
- Run setup.bat again
- Ensure Node.js v16+ is installed

## Next Steps

1. **Test the MVP** - Try multiple exercises, check scoring
2. **Gather Feedback** - Share with developers for input
3. **Plan Features** - Decide what to add next
4. **Scale Up** - Move to full DevFlow implementation

## Success Metrics

- Exercise completion rate
- User engagement time
- Accuracy improvement over attempts
- Feedback quality ratings

---

**Ready to revolutionize code review education? Start with this MVP and build from here!** 🌟