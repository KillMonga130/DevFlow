const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class ModelFineTuner {
  constructor() {
    this.trainingDataPath = path.join(__dirname, '../server/training-data');
    this.modelName = 'devflow-gpt';
  }

  async createModelfile() {
    const baseModel = 'gpt-oss:7b'; // Use faster base model
    
    const modelfile = `FROM ${baseModel}

# DevFlow-specific system prompt
SYSTEM """You are DevFlow AI, a specialized code review education assistant. You excel at:

1. Generating realistic code with intentional educational flaws
2. Analyzing code for security, performance, logic, and style issues  
3. Providing constructive, learning-focused feedback
4. Adapting explanations to user skill level

Always prioritize educational value and realistic scenarios that developers encounter in production environments.

For code generation: Create authentic-looking code with 2-4 intentional issues that match the requested difficulty and category.

For code analysis: Identify ALL issues with specific line numbers, categorize by type and severity, and provide actionable improvement suggestions.

For feedback: Be encouraging, specific, and focused on skill development rather than just correctness.
"""

# Optimize for speed and consistency
PARAMETER temperature 0.3
PARAMETER top_p 0.7
PARAMETER top_k 20
PARAMETER repeat_penalty 1.05
PARAMETER num_ctx 4096`;

    await fs.writeFile(path.join(__dirname, 'Modelfile'), modelfile);
    return path.join(__dirname, 'Modelfile');
  }

  async createFineTunedModel() {
    console.log('Creating DevFlow-optimized model...');
    
    const modelfilePath = await this.createModelfile();
    
    return new Promise((resolve, reject) => {
      const process = spawn('ollama', ['create', this.modelName, '-f', modelfilePath], {
        stdio: 'inherit'
      });

      process.on('close', (code) => {
        if (code === 0) {
          console.log(`✅ Created optimized model: ${this.modelName}`);
          resolve(this.modelName);
        } else {
          reject(new Error(`Model creation failed with code ${code}`));
        }
      });

      process.on('error', (error) => {
        reject(error);
      });
    });
  }

  async generateSyntheticTrainingData() {
    console.log('Generating synthetic training data...');
    
    const scenarios = [
      // Security scenarios
      { language: 'javascript', category: 'security', difficulty: 'beginner', description: 'SQL injection in user authentication' },
      { language: 'python', category: 'security', difficulty: 'intermediate', description: 'XSS vulnerability in web form' },
      { language: 'java', category: 'security', difficulty: 'advanced', description: 'Insecure deserialization' },
      
      // Performance scenarios  
      { language: 'javascript', category: 'performance', difficulty: 'beginner', description: 'Inefficient DOM manipulation' },
      { language: 'python', category: 'performance', difficulty: 'intermediate', description: 'N+1 database query problem' },
      { language: 'java', category: 'performance', difficulty: 'advanced', description: 'Memory leak in collection usage' },
      
      // Logic scenarios
      { language: 'javascript', category: 'logic', difficulty: 'beginner', description: 'Off-by-one error in array processing' },
      { language: 'python', category: 'logic', difficulty: 'intermediate', description: 'Race condition in async code' },
      { language: 'java', category: 'logic', difficulty: 'advanced', description: 'Incorrect exception handling flow' }
    ];

    const trainingExamples = [];

    for (const scenario of scenarios) {
      // Generate code examples with known issues
      const codeExample = await this.generateCodeExample(scenario);
      const analysis = await this.generateAnalysis(codeExample, scenario);
      
      trainingExamples.push({
        scenario,
        code: codeExample,
        analysis,
        timestamp: new Date().toISOString()
      });
    }

    // Save synthetic training data
    await fs.writeFile(
      path.join(this.trainingDataPath, 'synthetic-training-data.json'),
      JSON.stringify(trainingExamples, null, 2)
    );

    console.log(`Generated ${trainingExamples.length} synthetic training examples`);
    return trainingExamples;
  }

  async generateCodeExample(scenario) {
    // Pre-defined code templates with intentional issues
    const templates = {
      'javascript-security-beginner': `
function loginUser(username, password) {
  const query = "SELECT * FROM users WHERE username = '" + username + "' AND password = '" + password + "'";
  const result = db.query(query);
  
  if (result.length > 0) {
    console.log("Login successful for: " + username);
    return { success: true, user: result[0] };
  }
  
  return { success: false };
}`,
      
      'python-performance-intermediate': `
def get_user_posts(user_ids):
    posts = []
    for user_id in user_ids:
        user_posts = db.query("SELECT * FROM posts WHERE user_id = %s", user_id)
        for post in user_posts:
            post['author'] = db.query("SELECT name FROM users WHERE id = %s", post['user_id'])[0]
            posts.append(post)
    return posts`,
      
      'java-logic-advanced': `
public class CacheManager {
    private Map<String, Object> cache = new HashMap<>();
    
    public void updateCache(String key, Object value) {
        try {
            cache.put(key, value);
            notifyListeners(key, value);
        } catch (Exception e) {
            cache.remove(key);
            throw e;
        }
    }
    
    private void notifyListeners(String key, Object value) throws Exception {
        if (value == null) {
            throw new IllegalArgumentException("Value cannot be null");
        }
    }
}`
    };

    const templateKey = `${scenario.language}-${scenario.category}-${scenario.difficulty}`;
    return templates[templateKey] || `// ${scenario.description} example code`;
  }

  async generateAnalysis(code, scenario) {
    // Pre-defined analyses for synthetic examples
    const analyses = {
      'javascript-security-beginner': [
        {
          line: 2,
          type: 'security',
          severity: 'critical',
          title: 'SQL Injection Vulnerability',
          description: 'Direct string concatenation allows SQL injection attacks',
          suggestion: 'Use parameterized queries or prepared statements'
        },
        {
          line: 5,
          type: 'security', 
          severity: 'medium',
          title: 'Information Disclosure',
          description: 'Logging sensitive username information',
          suggestion: 'Log user IDs instead of usernames'
        }
      ]
    };

    const key = `${scenario.language}-${scenario.category}-${scenario.difficulty}`;
    return analyses[key] || [];
  }

  async optimizeModelForSpeed() {
    console.log('Optimizing model parameters for DevFlow...');
    
    // Create a speed-optimized version
    const speedModelfile = `FROM ${this.modelName}

# Speed optimizations for real-time use
PARAMETER num_ctx 2048
PARAMETER num_predict 512
PARAMETER temperature 0.2
PARAMETER top_p 0.6
PARAMETER top_k 15
PARAMETER repeat_penalty 1.1
PARAMETER num_thread -1
PARAMETER num_gpu -1`;

    await fs.writeFile(path.join(__dirname, 'SpeedModelfile'), speedModelfile);
    
    return new Promise((resolve, reject) => {
      const process = spawn('ollama', ['create', `${this.modelName}-fast`, '-f', path.join(__dirname, 'SpeedModelfile')], {
        stdio: 'inherit'
      });

      process.on('close', (code) => {
        if (code === 0) {
          console.log(`✅ Created speed-optimized model: ${this.modelName}-fast`);
          resolve(`${this.modelName}-fast`);
        } else {
          reject(new Error(`Speed optimization failed with code ${code}`));
        }
      });
    });
  }

  async run() {
    try {
      console.log('🚀 Starting DevFlow model fine-tuning process...\n');
      
      // Step 1: Generate synthetic training data
      await this.generateSyntheticTrainingData();
      
      // Step 2: Create base fine-tuned model
      const modelName = await this.createFineTunedModel();
      
      // Step 3: Create speed-optimized version
      const fastModelName = await this.optimizeModelForSpeed();
      
      console.log('\n✅ Fine-tuning complete!');
      console.log(`Base model: ${modelName}`);
      console.log(`Fast model: ${fastModelName}`);
      console.log('\nUpdate your .env file:');
      console.log(`OLLAMA_MODEL=${fastModelName}`);
      
    } catch (error) {
      console.error('❌ Fine-tuning failed:', error.message);
      process.exit(1);
    }
  }
}

// Run if called directly
if (require.main === module) {
  const tuner = new ModelFineTuner();
  tuner.run();
}

module.exports = ModelFineTuner;