const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const OllamaService = require('./ollama-service');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize database
const db = new sqlite3.Database('./devflow-mvp.db');

// Initialize Ollama service
const ollama = new OllamaService();

// Create tables
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    issues TEXT NOT NULL,
    language TEXT DEFAULT 'javascript',
    difficulty TEXT DEFAULT 'beginner',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER,
    user_issues TEXT,
    score INTEGER,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exercise_id) REFERENCES exercises(id)
  )`);
});

// Routes
app.get('/api/health', async (req, res) => {
  const aiAvailable = await ollama.isAvailable();
  res.json({ 
    status: 'DevFlow MVP is running!',
    ai: aiAvailable ? 'Connected' : 'Demo mode'
  });
});

// Generate new exercise
app.post('/api/exercise/generate', async (req, res) => {
  try {
    console.log('Generating new exercise...');
    
    // Generate code with AI or use demo
    const code = await ollama.generateCode();
    const issues = await ollama.analyzeCode(code);
    
    // Save to database
    db.run(
      'INSERT INTO exercises (code, issues) VALUES (?, ?)',
      [code, JSON.stringify(issues)],
      function(err) {
        if (err) {
          console.error('Database error:', err);
          return res.status(500).json({ error: 'Failed to save exercise' });
        }
        
        res.json({
          id: this.lastID,
          code,
          // Don't send issues to client yet
          message: 'Exercise generated successfully'
        });
      }
    );
  } catch (error) {
    console.error('Error generating exercise:', error);
    res.status(500).json({ error: 'Failed to generate exercise' });
  }
});

// Submit review
app.post('/api/exercise/:id/submit', (req, res) => {
  const { id } = req.params;
  const { userIssues } = req.body;
  
  // Get the correct issues
  db.get('SELECT * FROM exercises WHERE id = ?', [id], (err, exercise) => {
    if (err) {
      return res.status(500).json({ error: 'Database error' });
    }
    
    if (!exercise) {
      return res.status(404).json({ error: 'Exercise not found' });
    }
    
    const correctIssues = JSON.parse(exercise.issues);
    const foundIssues = userIssues || [];
    
    // Calculate score
    const totalIssues = correctIssues.length;
    const correctlyFound = foundIssues.filter(found => 
      correctIssues.some(correct => 
        Math.abs(found.line - correct.line) <= 1 && 
        found.type === correct.type
      )
    ).length;
    
    const score = totalIssues > 0 ? Math.round((correctlyFound / totalIssues) * 100) : 0;
    
    // Save attempt
    db.run(
      'INSERT INTO attempts (exercise_id, user_issues, score) VALUES (?, ?, ?)',
      [id, JSON.stringify(foundIssues), score],
      function(err) {
        if (err) {
          console.error('Error saving attempt:', err);
        }
        
        // Return results
        res.json({
          score,
          correctIssues,
          foundIssues,
          feedback: generateFeedback(score, correctlyFound, totalIssues)
        });
      }
    );
  });
});

// Get stats
app.get('/api/stats', (req, res) => {
  db.all(`
    SELECT 
      COUNT(*) as totalAttempts,
      AVG(score) as averageScore,
      MAX(score) as bestScore
    FROM attempts
  `, [], (err, rows) => {
    if (err) {
      return res.status(500).json({ error: 'Database error' });
    }
    
    const stats = rows[0] || { totalAttempts: 0, averageScore: 0, bestScore: 0 };
    res.json(stats);
  });
});

function generateFeedback(score, found, total) {
  if (score >= 90) {
    return {
      message: "Excellent! You caught almost all the issues.",
      level: "expert",
      tip: "You have sharp code review skills!"
    };
  } else if (score >= 70) {
    return {
      message: `Good work! You found ${found} out of ${total} issues.`,
      level: "good",
      tip: "Look more carefully for edge cases and security issues."
    };
  } else if (score >= 50) {
    return {
      message: `Not bad! You found ${found} out of ${total} issues.`,
      level: "okay",
      tip: "Focus on common patterns like input validation and error handling."
    };
  } else {
    return {
      message: `Keep practicing! You found ${found} out of ${total} issues.`,
      level: "beginner",
      tip: "Start by looking for obvious issues like missing validation and security flaws."
    };
  }
}

app.listen(PORT, () => {
  console.log(`🚀 DevFlow MVP server running on port ${PORT}`);
  console.log(`📊 Database: devflow-mvp.db`);
  console.log(`🤖 AI: Checking Ollama connection...`);
  
  // Test AI connection
  ollama.isAvailable().then(available => {
    console.log(`🤖 AI Status: ${available ? 'Connected to Ollama' : 'Demo mode (Ollama not available)'}`);
  });
});