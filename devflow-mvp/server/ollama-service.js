const axios = require('axios');

class OllamaService {
  constructor() {
    this.baseURL = 'http://localhost:11434';
    this.model = 'gpt-oss:20b';
    this.available = null;
  }

  async isAvailable() {
    if (this.available !== null) return this.available;
    
    try {
      const response = await axios.get(`${this.baseURL}/api/tags`, { timeout: 1000 });
      const models = response.data.models || [];
      this.available = models.some(m => m.name.includes('gpt-oss'));
      console.log(`AI Status: ${this.available ? 'Connected' : 'Not available'}`);
      return this.available;
    } catch (error) {
      console.log('AI not available, using demo mode');
      this.available = false;
      return false;
    }
  }

  async generateCode() {
    if (await this.isAvailable()) {
      try {
        return await this.generateWithAI();
      } catch (error) {
        console.log('AI generation failed, using demo code');
      }
    }
    
    return this.getDemoCode();
  }

  async generateWithAI() {
    const prompt = `Generate a simple JavaScript function with 2-3 intentional bugs for code review practice. 

Make it realistic - something a junior developer might write. Include common issues like:
- Missing input validation
- Security vulnerabilities  
- Logic errors
- Performance issues

Keep it 10-15 lines. Return ONLY the code:`;

    const response = await axios.post(`${this.baseURL}/api/generate`, {
      model: this.model,
      prompt,
      stream: false,
      options: {
        temperature: 0.7,
        max_tokens: 200
      }
    });

    return response.data.response.trim();
  }

  getDemoCode() {
    const demoExercises = [
      `function authenticateUser(username, password) {
    const query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
    const result = database.query(query);
    
    if (result.length > 0) {
        console.log("Login successful for: " + username);
        return { success: true, user: result[0] };
    }
    
    return { success: false };
}`,

      `function processUserData(userData) {
    let result = [];
    
    for (let i = 0; i < userData.length; i++) {
        if (userData[i].age > 18) {
            result.push({
                name: userData[i].name,
                email: userData[i].email,
                isAdult: true
            });
        }
    }
    
    return result.sort();
}`,

      `function calculateDiscount(price, userType) {
    let discount = 0;
    
    if (userType == "premium") {
        discount = price * 0.2;
    } else if (userType == "regular") {
        discount = price * 0.1;
    }
    
    const finalPrice = price - discount;
    return finalPrice;
}`,

      `function uploadFile(file) {
    const allowedTypes = ['jpg', 'png', 'gif'];
    const fileExtension = file.name.split('.').pop();
    
    if (allowedTypes.includes(fileExtension)) {
        const uploadPath = '/uploads/' + file.name;
        saveFile(uploadPath, file.content);
        return { success: true, path: uploadPath };
    }
    
    return { success: false, error: 'Invalid file type' };
}`
    ];

    return demoExercises[Math.floor(Math.random() * demoExercises.length)];
  }

  async analyzeCode(code) {
    if (await this.isAvailable()) {
      try {
        return await this.analyzeWithAI(code);
      } catch (error) {
        console.log('AI analysis failed, using demo analysis');
      }
    }
    
    return this.getDemoAnalysis(code);
  }

  async analyzeWithAI(code) {
    const prompt = `Analyze this JavaScript code and identify ALL issues. Return as JSON array:

${code}

Format: [{"line": 2, "type": "security", "title": "SQL Injection", "description": "Direct string concatenation allows injection"}]

Types: security, performance, logic, style
Return ONLY the JSON array:`;

    const response = await axios.post(`${this.baseURL}/api/generate`, {
      model: this.model,
      prompt,
      stream: false,
      options: {
        temperature: 0.3,
        max_tokens: 300
      }
    });

    try {
      const jsonMatch = response.data.response.match(/\[[\s\S]*\]/);
      if (jsonMatch) {
        return JSON.parse(jsonMatch[0]);
      }
    } catch (error) {
      console.log('Failed to parse AI analysis, using demo');
    }
    
    return this.getDemoAnalysis(code);
  }

  getDemoAnalysis(code) {
    // Smart demo analysis based on code content
    const issues = [];
    const lines = code.split('\n');
    
    lines.forEach((line, index) => {
      const lineNum = index + 1;
      
      // Check for SQL injection
      if (line.includes("SELECT * FROM") && line.includes("' +")) {
        issues.push({
          line: lineNum,
          type: "security",
          title: "SQL Injection Vulnerability",
          description: "Direct string concatenation in SQL query allows injection attacks"
        });
      }
      
      // Check for console.log
      if (line.includes("console.log") && line.includes("username")) {
        issues.push({
          line: lineNum,
          type: "security",
          title: "Information Disclosure",
          description: "Logging sensitive user information"
        });
      }
      
      // Check for == instead of ===
      if (line.includes(" == ") && !line.includes("===")) {
        issues.push({
          line: lineNum,
          type: "logic",
          title: "Loose Equality Comparison",
          description: "Use strict equality (===) instead of loose equality (==)"
        });
      }
      
      // Check for missing input validation
      if (line.includes("function") && (line.includes("username") || line.includes("password") || line.includes("userData"))) {
        issues.push({
          line: lineNum,
          type: "security",
          title: "Missing Input Validation",
          description: "No validation for input parameters"
        });
      }
      
      // Check for file upload issues
      if (line.includes("file.name") && line.includes("split")) {
        issues.push({
          line: lineNum,
          type: "security",
          title: "Path Traversal Risk",
          description: "File name not sanitized, could allow directory traversal"
        });
      }
      
      // Check for inefficient sorting
      if (line.includes(".sort()") && !line.includes("sort(")) {
        issues.push({
          line: lineNum,
          type: "performance",
          title: "Inefficient Sorting",
          description: "Sorting without comparison function may not work as expected"
        });
      }
    });
    
    // Ensure we always have at least 2 issues for demo
    if (issues.length < 2) {
      issues.push({
        line: 1,
        type: "style",
        title: "Missing Error Handling",
        description: "Function should handle potential errors and edge cases"
      });
    }
    
    return issues;
  }
}

module.exports = OllamaService;