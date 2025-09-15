const axios = require('axios');

class SimpleOllamaService {
  constructor(baseURL = 'http://localhost:11434') {
    this.baseURL = baseURL;
    this.model = 'gpt-oss:20b';
    this.aiAvailable = null; // Cache AI availability
  }

  // Enhanced version - tries AI first, falls back to demo content
  async generateCodeWithIssues(language, difficulty, category, description) {
    console.log(`Generating ${language} ${difficulty} ${category} exercise...`);
    
    // Try AI first if available
    if (await this.checkAI()) {
      try {
        return await this.generateWithAI(language, difficulty, category, description);
      } catch (error) {
        console.log('AI generation failed, using demo content:', error.message);
      }
    }
    
    // Fallback to demo content
    const demoCode = this.getDemoCode(language, category);
    console.log('Demo code generated successfully');
    return demoCode;
  }

  async generateWithAI(language, difficulty, category, description) {
    const prompt = `Generate realistic ${language} code for a ${difficulty} level code review exercise focusing on ${category} issues.

Requirements:
- Create code that has 2-3 intentional ${category} issues
- Make it realistic - something a developer might actually write
- Include common mistakes for ${difficulty} level developers
- Focus on: ${description}

The code should be 10-20 lines and contain realistic bugs.

Return ONLY the code, no explanations:`;

    const response = await axios.post(`${this.baseURL}/api/generate`, {
      model: this.model,
      prompt: prompt,
      stream: false,
      options: {
        temperature: 0.7,
        max_tokens: 300
      }
    });

    return response.data.response.trim();
  }

  async checkAI() {
    if (this.aiAvailable !== null) return this.aiAvailable;
    
    try {
      const response = await axios.get(`${this.baseURL}/api/tags`, { timeout: 2000 });
      const models = response.data.models || [];
      this.aiAvailable = models.some(m => m.name.includes('gpt-oss'));
      return this.aiAvailable;
    } catch (error) {
      this.aiAvailable = false;
      return false;
    }
  }

  getDemoCode(language, category) {
    const codes = {
      javascript: {
        security: `function authenticateUser(username, password) {
    const query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
    const result = database.query(query);
    
    if (result.length > 0) {
        console.log("Login successful for: " + username);
        return { success: true, user: result[0] };
    }
    
    return { success: false };
}`,
        performance: `function processData(items) {
    let result = [];
    
    for (let i = 0; i < items.length; i++) {
        for (let j = 0; j < items.length; j++) {
            if (items[i].category === items[j].category && i !== j) {
                result.push({ item: items[i], related: items[j] });
            }
        }
    }
    
    return result.sort((a, b) => a.item.name > b.item.name ? 1 : -1);
}`,
        logic: `function processFile(filePath) {
    const file = fs.openSync(filePath, 'r');
    const content = fs.readFileSync(file, 'utf8');
    
    if (content.length > 0) {
        const lines = content.split('\\n');
        const processed = lines.filter(line => line.trim()).map(line => line.toUpperCase());
        
        fs.closeSync(file);
        return processed;
    }
    
    return [];
}`
      },
      python: {
        security: `def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    result = database.execute(query)
    
    if len(result) > 0:
        print(f"Login successful for: {username}")
        return {"success": True, "user": result[0]}
    
    return {"success": False}`,
        performance: `def process_data(items):
    result = []
    
    for i in range(len(items)):
        for j in range(len(items)):
            if items[i]['category'] == items[j]['category'] and i != j:
                result.append({'item': items[i], 'related': items[j]})
    
    return sorted(result, key=lambda x: x['item']['name'])`,
        logic: `def process_file(file_path):
    file = open(file_path, 'r')
    content = file.read()
    
    if len(content) > 0:
        lines = content.split('\\n')
        processed = [line.upper() for line in lines if line.strip()]
        
        file.close()
        return processed
    
    return []`
      }
    };

    return codes[language]?.[category] || codes.javascript.security;
  }

  async analyzeCodeIssues(code, language) {
    console.log('Analyzing code issues...');
    
    // Return demo analysis immediately
    return [
      {
        line: 2,
        type: "security",
        severity: "critical",
        title: "SQL Injection Vulnerability",
        description: "Direct string concatenation in SQL query allows injection attacks",
        suggestion: "Use parameterized queries or prepared statements"
      },
      {
        line: 5,
        type: "security",
        severity: "medium",
        title: "Information Disclosure",
        description: "Logging sensitive user information",
        suggestion: "Log user IDs instead of usernames"
      },
      {
        line: 8,
        type: "logic",
        severity: "low",
        title: "Missing Input Validation",
        description: "No validation for empty or null inputs",
        suggestion: "Add input validation before processing"
      }
    ];
  }

  async generatePersonalizedFeedback(userIssues, correctIssues, score, category) {
    return `Great work on this ${category} review! You scored ${score}%. You found ${userIssues.length} out of ${correctIssues.length} issues. Keep practicing to improve your code review skills!`;
  }

  async generateLearningPath(userSkills, weakestArea) {
    return `Focus on improving your ${weakestArea} skills. Practice more exercises in this area and review common patterns.`;
  }

  async isModelAvailable() {
    try {
      const response = await axios.get(`${this.baseURL}/api/tags`);
      console.log('Ollama is available');
      return true;
    } catch (error) {
      console.log('Ollama not available, using demo mode');
      return false;
    }
  }
}

module.exports = SimpleOllamaService;