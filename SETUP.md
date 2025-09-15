# DevFlow Setup Instructions

## Quick Start (Windows)

1. **Run the setup script:**
   ```bash
   start-devflow.bat
   ```

## Manual Setup

### 1. Install Server Dependencies
```bash
cd server
npm install
```

### 2. Set Up Database
```bash
cd server
node seedData.js
```

### 3. Start Backend Server
```bash
cd server
npm run dev
```

### 4. Start Frontend (in new terminal)
```bash
cd client
npm start
```

## Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:3001

## Troubleshooting

### "Cannot find module" errors
- Make sure you've installed dependencies in both `client/` and `server/` directories
- Run `npm install` in the root directory first

### Database errors
- Make sure you've run `node seedData.js` in the server directory
- Check that SQLite is working properly

### Port conflicts
- Backend runs on port 3001
- Frontend runs on port 3000
- Make sure these ports are available

## Project Structure

```
DevFlow/
├── client/                 # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── App.tsx         # Main app component
│   │   └── index.tsx       # Entry point
│   └── package.json
├── server/                 # Node.js backend
│   ├── index.js           # Express server
│   ├── seedData.js        # Database setup
│   └── package.json
├── .kiro/                 # Kiro configuration
│   ├── specs/             # Project specifications
│   ├── hooks/             # Agent hooks
│   └── steering/          # Development guidelines
└── README.md
```

## Demo Features

1. **Exercise List** - Browse code review exercises with filtering
2. **Interactive Review** - Annotate code issues with real-time feedback
3. **Progress Tracking** - View skill development and achievements
4. **Realistic Examples** - Practice on flawed code with security, performance, and logic issues