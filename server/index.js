const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const http = require('http');
const socketIo = require('socket.io');
const OllamaService = require('./simple-ollama-service');
const AnalyticsService = require('./analytics-service');
const AchievementSystem = require('./achievement-system');
const ModelPerformanceTracker = require('./model-performance-tracker');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 3001;

// Initialize database
const dbPath = path.join(__dirname, 'devflow.db');
const db = new sqlite3.Database(dbPath);

// Initialize services
const ollama = new OllamaService();
const analyticsService = new AnalyticsService();
const achievementSystem = new AchievementSystem(db);
const performanceTracker = new ModelPerformanceTracker();

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));



// Initialize database tables
db.serialize(() => {
  // Users table
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    skill_level TEXT DEFAULT 'beginner',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // Code review exercises
  db.run(`CREATE TABLE IF NOT EXISTS review_exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    code_content TEXT NOT NULL,
    issues_json TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);

  // User review attempts
  db.run(`CREATE TABLE IF NOT EXISTS review_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    exercise_id INTEGER,
    issues_found_json TEXT,
    review_comments TEXT,
    score INTEGER,
    time_spent INTEGER,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (exercise_id) REFERENCES review_exercises(id)
  )`);

  // User skill progress
  db.run(`CREATE TABLE IF NOT EXISTS skill_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    skill_category TEXT,
    accuracy_score REAL DEFAULT 0,
    exercises_completed INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
  )`);
});

// Routes
app.get('/api/health', async (req, res) => {
  const ollamaAvailable = await ollama.isModelAvailable();
  res.json({ 
    status: 'DevFlow API is running!',
    ai_powered: ollamaAvailable,
    model: ollamaAvailable ? 'gpt-oss available' : 'AI features disabled'
  });
});

// AI-powered exercise generation
app.post('/api/exercises/generate', async (req, res) => {
  try {
    const { language, difficulty, category, description } = req.body;
    
    console.log('Generating AI-powered exercise...');
    const code = await ollama.generateCodeWithIssues(language, difficulty, category, description);
    const issues = await ollama.analyzeCodeIssues(code, language);
    
    // Save to database
    const title = `AI Generated ${category.charAt(0).toUpperCase() + category.slice(1)} Exercise`;
    const exerciseDescription = description || `Practice identifying ${category} issues in ${language} code`;
    
    db.run(
      `INSERT INTO review_exercises 
       (language, difficulty, category, title, description, code_content, issues_json) 
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [language, difficulty, category, title, exerciseDescription, code, JSON.stringify(issues)],
      function(err) {
        if (err) {
          res.status(500).json({ error: err.message });
          return;
        }
        
        res.json({
          id: this.lastID,
          language,
          difficulty,
          category,
          title,
          description: exerciseDescription,
          code_content: code,
          issues,
          ai_generated: true
        });
      }
    );
  } catch (error) {
    console.error('Error generating AI exercise:', error);
    res.status(500).json({ error: 'Failed to generate AI-powered exercise' });
  }
});

// AI-powered code analysis
app.post('/api/code/analyze', async (req, res) => {
  try {
    const { code, language } = req.body;
    
    console.log('Analyzing code with AI...');
    const issues = await ollama.analyzeCodeIssues(code, language);
    
    res.json({
      issues,
      ai_powered: true,
      analysis_timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error analyzing code:', error);
    res.status(500).json({ error: 'Failed to analyze code with AI' });
  }
});

// Get all exercises
app.get('/api/exercises', (req, res) => {
  const { language, difficulty, category } = req.query;
  
  let query = 'SELECT * FROM review_exercises WHERE 1=1';
  const params = [];
  
  if (language) {
    query += ' AND language = ?';
    params.push(language);
  }
  
  if (difficulty) {
    query += ' AND difficulty = ?';
    params.push(difficulty);
  }
  
  if (category) {
    query += ' AND category = ?';
    params.push(category);
  }
  
  query += ' ORDER BY created_at DESC';
  
  db.all(query, params, (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    
    // Parse issues_json for each exercise
    const exercises = rows.map(row => ({
      ...row,
      issues: JSON.parse(row.issues_json)
    }));
    
    res.json(exercises);
  });
});

// Get specific exercise
app.get('/api/exercises/:id', (req, res) => {
  const { id } = req.params;
  
  db.get('SELECT * FROM review_exercises WHERE id = ?', [id], (err, row) => {
    if (err) {
      res.status(500).json({ error: err.message });
      return;
    }
    
    if (!row) {
      res.status(404).json({ error: 'Exercise not found' });
      return;
    }
    
    const exercise = {
      ...row,
      issues: JSON.parse(row.issues_json)
    };
    
    res.json(exercise);
  });
});

// Submit review attempt with advanced analytics and achievements
app.post('/api/exercises/:id/submit', async (req, res) => {
  const { id } = req.params;
  const { userId, issuesFound, reviewComments, timeSpent } = req.body;
  
  const startTime = Date.now();
  
  try {
    // Get the exercise to compare against correct issues
    const exercise = await new Promise((resolve, reject) => {
      db.get('SELECT * FROM review_exercises WHERE id = ?', [id], (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
    
    if (!exercise) {
      return res.status(404).json({ error: 'Exercise not found' });
    }
    
    const correctIssues = JSON.parse(exercise.issues_json);
    const foundIssues = issuesFound || [];
    
    // Calculate detailed scoring
    const totalIssues = correctIssues.length;
    const correctlyFound = foundIssues.filter(found => 
      correctIssues.some(correct => 
        Math.abs(found.line - correct.line) <= 2 && 
        found.type === correct.type
      )
    ).length;
    
    const score = Math.round((correctlyFound / totalIssues) * 100);
    const accuracy = correctlyFound / Math.max(totalIssues, 1);
    
    // Save the attempt
    const attemptId = await new Promise((resolve, reject) => {
      db.run(
        `INSERT INTO review_attempts 
         (user_id, exercise_id, issues_found_json, review_comments, score, time_spent) 
         VALUES (?, ?, ?, ?, ?, ?)`,
        [userId, id, JSON.stringify(foundIssues), reviewComments, score, timeSpent],
        function(err) {
          if (err) reject(err);
          else resolve(this.lastID);
        }
      );
    });

    // Track analytics
    await analyticsService.trackExerciseCompletion(userId, {
      exerciseId: id,
      language: exercise.language,
      difficulty: exercise.difficulty,
      category: exercise.category,
      timeToComplete: timeSpent,
      issuesFound: foundIssues.length,
      issuesCorrect: correctlyFound,
      hintsUsed: req.body.hintsUsed || 0,
      userFeedbackRating: null // Will be updated later
    });

    // Check for new achievements
    const newAchievements = await achievementSystem.checkAchievements(userId, {
      exerciseCompleted: true,
      score: accuracy,
      timeToComplete: timeSpent,
      category: exercise.category,
      language: exercise.language
    });

    // Track model performance
    const responseTime = performanceTracker.trackResponseTime(startTime, Date.now());
    performanceTracker.trackAccuracy(foundIssues, correctIssues);

    // Generate AI-powered personalized feedback
    let aiFeedback = '';
    try {
      aiFeedback = await ollama.generatePersonalizedFeedback(
        foundIssues, 
        correctIssues, 
        score, 
        exercise.category
      );
    } catch (error) {
      console.error('AI feedback generation failed:', error);
      aiFeedback = 'Great effort on this review! Keep practicing to improve your skills.';
    }

    // Emit real-time updates to connected clients
    io.to(`user_${userId}`).emit('exerciseCompleted', {
      score,
      newAchievements,
      levelUp: newAchievements.some(a => a.type === 'milestone')
    });

    // Broadcast achievements to all users (for motivation)
    if (newAchievements.length > 0) {
      io.emit('newAchievement', {
        userId,
        achievements: newAchievements.map(a => ({ name: a.name, icon: a.icon }))
      });
    }

    res.json({
      attemptId,
      score,
      accuracy: Math.round(accuracy * 100),
      correctIssues,
      foundIssues,
      newAchievements,
      feedback: {
        ...generateFeedback(correctIssues, foundIssues, score),
        ai_feedback: aiFeedback,
        ai_powered: true,
        response_time: responseTime
      }
    });

  } catch (error) {
    console.error('Error submitting review:', error);
    res.status(500).json({ error: 'Failed to submit review' });
  }
});

// Helper function to generate feedback
function generateFeedback(correctIssues, foundIssues, score) {
  const feedback = {
    overall: '',
    missed: [],
    incorrect: [],
    suggestions: []
  };
  
  if (score >= 80) {
    feedback.overall = 'Excellent work! You caught most of the critical issues.';
  } else if (score >= 60) {
    feedback.overall = 'Good effort! There are a few more issues to spot.';
  } else {
    feedback.overall = 'Keep practicing! Code review takes time to master.';
  }
  
  // Find missed issues
  correctIssues.forEach(correct => {
    const found = foundIssues.find(f => 
      Math.abs(f.line - correct.line) <= 2 && f.type === correct.type
    );
    if (!found) {
      feedback.missed.push(correct);
    }
  });
  
  // Add suggestions based on performance
  if (feedback.missed.length > 0) {
    feedback.suggestions.push('Focus on scanning for common patterns like security vulnerabilities and performance bottlenecks.');
  }
  
  return feedback;
}

// New API endpoints for advanced features

// Get user analytics and insights
app.get('/api/users/:userId/analytics', async (req, res) => {
  try {
    const { userId } = req.params;
    const insights = await analyticsService.getUserLearningInsights(userId);
    res.json(insights);
  } catch (error) {
    console.error('Error fetching user analytics:', error);
    res.status(500).json({ error: 'Failed to fetch analytics' });
  }
});

// Get user progress and achievements
app.get('/api/users/:userId/progress', async (req, res) => {
  try {
    const { userId } = req.params;
    
    // Get basic stats
    const stats = await new Promise((resolve, reject) => {
      db.get(`
        SELECT 
          COUNT(*) as totalExercises,
          AVG(score) as averageScore,
          MAX(score) as bestScore
        FROM review_attempts 
        WHERE user_id = ?
      `, [userId], (err, row) => {
        if (err) reject(err);
        else resolve(row || {});
      });
    });

    // Get skill levels by category
    const skillLevels = await new Promise((resolve, reject) => {
      db.all(`
        SELECT 
          re.category,
          AVG(ra.score) as avgScore,
          COUNT(*) as exerciseCount
        FROM review_attempts ra
        JOIN review_exercises re ON ra.exercise_id = re.id
        WHERE ra.user_id = ?
        GROUP BY re.category
      `, [userId], (err, rows) => {
        if (err) reject(err);
        else {
          const skills = {};
          rows.forEach(row => {
            skills[row.category] = Math.round(row.avgScore || 0);
          });
          resolve(skills);
        }
      });
    });

    // Get achievements
    const achievements = await achievementSystem.getUserAchievements(userId);
    
    // Calculate streak (simplified)
    const streak = Math.floor(Math.random() * 15) + 1; // Placeholder
    const weeklyProgress = Math.floor(Math.random() * 7) + 1; // Placeholder

    res.json({
      stats: {
        totalExercises: stats.totalExercises || 0,
        averageScore: Math.round(stats.averageScore || 0),
        bestScore: stats.bestScore || 0,
        streak,
        skillLevels,
        badges: achievements,
        weeklyGoal: 5,
        weeklyProgress
      },
      recentAchievements: achievements.slice(0, 3)
    });
  } catch (error) {
    console.error('Error fetching user progress:', error);
    res.status(500).json({ error: 'Failed to fetch progress' });
  }
});

// Get leaderboard
app.get('/api/leaderboard', async (req, res) => {
  try {
    const { category = 'overall', limit = 10 } = req.query;
    const leaderboard = await achievementSystem.getLeaderboard(category, parseInt(limit));
    res.json(leaderboard);
  } catch (error) {
    console.error('Error fetching leaderboard:', error);
    res.status(500).json({ error: 'Failed to fetch leaderboard' });
  }
});

// Rate exercise feedback
app.post('/api/exercises/:id/rate', async (req, res) => {
  try {
    const { id } = req.params;
    const { userId, rating } = req.body;
    
    // Update the latest attempt with feedback rating
    db.run(`
      UPDATE review_attempts 
      SET user_feedback_rating = ?
      WHERE user_id = ? AND exercise_id = ?
      ORDER BY completed_at DESC
      LIMIT 1
    `, [rating, userId, id]);

    // Track user satisfaction
    performanceTracker.trackUserSatisfaction(rating, 'exercise');
    
    res.json({ success: true });
  } catch (error) {
    console.error('Error rating exercise:', error);
    res.status(500).json({ error: 'Failed to rate exercise' });
  }
});

// Get model performance metrics
app.get('/api/admin/performance', async (req, res) => {
  try {
    const report = performanceTracker.getPerformanceReport();
    const shouldRetrain = performanceTracker.shouldRetrain();
    
    res.json({
      ...report,
      shouldRetrain,
      recommendations: shouldRetrain ? [
        'Consider retraining the model with recent data',
        'Check for model degradation patterns',
        'Review user feedback for quality issues'
      ] : []
    });
  } catch (error) {
    console.error('Error fetching performance metrics:', error);
    res.status(500).json({ error: 'Failed to fetch performance metrics' });
  }
});

// Real-time socket connections
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);
  
  socket.on('joinUser', (userId) => {
    socket.join(`user_${userId}`);
    console.log(`User ${userId} joined their room`);
  });

  socket.on('startExercise', (data) => {
    // Track exercise start for analytics
    console.log(`User ${data.userId} started exercise ${data.exerciseId}`);
  });

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
  });
});

server.listen(PORT, () => {
  console.log(`🚀 DevFlow server running on port ${PORT}`);
  console.log(`📊 Analytics enabled`);
  console.log(`🏆 Achievement system active`);
  console.log(`🤖 AI model performance tracking enabled`);
});