const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.join(__dirname, 'devflow.db');
const db = new sqlite3.Database(dbPath);

// Sample exercises with intentional issues
const exercises = [
  {
    language: 'javascript',
    difficulty: 'beginner',
    category: 'security',
    title: 'User Authentication Function',
    description: 'Review this login function for security issues',
    code_content: `function authenticateUser(username, password) {
    const query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
    const result = database.query(query);
    
    if (result.length > 0) {
        console.log("Login successful for: " + username);
        return { success: true, user: result[0] };
    }
    
    return { success: false };
}`,
    issues: [
      {
        line: 2,
        type: 'security',
        severity: 'critical',
        title: 'SQL Injection Vulnerability',
        description: 'Direct string concatenation in SQL query allows SQL injection attacks',
        suggestion: 'Use parameterized queries or prepared statements'
      },
      {
        line: 2,
        type: 'security',
        severity: 'critical',
        title: 'Plain Text Password Storage',
        description: 'Passwords should never be stored or compared in plain text',
        suggestion: 'Use bcrypt or similar hashing library for password comparison'
      },
      {
        line: 5,
        type: 'security',
        severity: 'medium',
        title: 'Information Disclosure',
        description: 'Logging usernames can expose sensitive information',
        suggestion: 'Log user IDs instead of usernames, or use structured logging'
      }
    ]
  },
  {
    language: 'javascript',
    difficulty: 'intermediate',
    category: 'performance',
    title: 'Data Processing Function',
    description: 'Review this data processing code for performance issues',
    code_content: `function processUserData(users) {
    let result = [];
    
    for (let i = 0; i < users.length; i++) {
        for (let j = 0; j < users.length; j++) {
            if (users[i].department === users[j].department && i !== j) {
                result.push({
                    user: users[i],
                    colleague: users[j]
                });
            }
        }
    }
    
    // Sort results
    for (let i = 0; i < result.length; i++) {
        for (let j = i + 1; j < result.length; j++) {
            if (result[i].user.name > result[j].user.name) {
                let temp = result[i];
                result[i] = result[j];
                result[j] = temp;
            }
        }
    }
    
    return result;
}`,
    issues: [
      {
        line: 4,
        type: 'performance',
        severity: 'high',
        title: 'O(n²) Nested Loop',
        description: 'Nested loops create quadratic time complexity for finding colleagues',
        suggestion: 'Group users by department first, then process each group'
      },
      {
        line: 14,
        type: 'performance',
        severity: 'medium',
        title: 'Inefficient Bubble Sort',
        description: 'Manual bubble sort implementation is slower than built-in sort',
        suggestion: 'Use Array.sort() with a custom comparator function'
      },
      {
        line: 2,
        type: 'style',
        severity: 'low',
        title: 'Array Initialization',
        description: 'Could use more descriptive variable name',
        suggestion: 'Consider naming it "colleagues" or "departmentPairs"'
      }
    ]
  },
  {
    language: 'python',
    difficulty: 'beginner',
    category: 'logic',
    title: 'File Processing Script',
    description: 'Review this file processing code for logical errors',
    code_content: `def process_files(file_paths):
    results = []
    
    for path in file_paths:
        file = open(path, 'r')
        content = file.read()
        
        if len(content) > 0:
            lines = content.split('\\n')
            processed = []
            
            for line in lines:
                if line.strip():
                    processed.append(line.upper())
            
            results.append({
                'file': path,
                'lines': len(processed),
                'content': processed
            })
        
        file.close()
    
    return results`,
    issues: [
      {
        line: 5,
        type: 'logic',
        severity: 'high',
        title: 'Resource Leak',
        description: 'File is not properly closed if an exception occurs',
        suggestion: 'Use "with open()" context manager for automatic file handling'
      },
      {
        line: 4,
        type: 'logic',
        severity: 'medium',
        title: 'No Error Handling',
        description: 'No handling for files that don\'t exist or can\'t be read',
        suggestion: 'Add try-except blocks to handle FileNotFoundError and PermissionError'
      },
      {
        line: 7,
        type: 'logic',
        severity: 'low',
        title: 'Redundant Length Check',
        description: 'Empty content check is unnecessary since split() handles empty strings',
        suggestion: 'Remove the length check or make it more meaningful'
      }
    ]
  }
];

// Insert seed data
db.serialize(() => {
  const stmt = db.prepare(`
    INSERT INTO review_exercises 
    (language, difficulty, category, title, description, code_content, issues_json) 
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `);
  
  exercises.forEach(exercise => {
    stmt.run(
      exercise.language,
      exercise.difficulty,
      exercise.category,
      exercise.title,
      exercise.description,
      exercise.code_content,
      JSON.stringify(exercise.issues)
    );
  });
  
  stmt.finalize();
  
  console.log('Seed data inserted successfully!');
  db.close();
});

module.exports = exercises;