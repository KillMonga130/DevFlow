#!/usr/bin/env node

const OllamaService = require('./ollama-service');

async function testAISpeed() {
  console.log('🧪 Testing AI Generation Speed...\n');
  
  const ollama = new OllamaService();
  
  // Check if AI is available
  const available = await ollama.isModelAvailable();
  if (!available) {
    console.log('❌ AI service not available');
    return;
  }
  
  console.log('✅ AI service is available\n');
  
  // Test different scenarios
  const tests = [
    {
      name: 'Quick Security Exercise',
      language: 'javascript',
      difficulty: 'beginner',
      category: 'security',
      description: 'Simple login function'
    },
    {
      name: 'Performance Exercise',
      language: 'javascript',
      difficulty: 'intermediate',
      category: 'performance',
      description: 'Data processing loop'
    }
  ];
  
  for (const test of tests) {
    console.log(`🚀 Testing: ${test.name}`);
    const startTime = Date.now();
    
    try {
      const result = await ollama.generateCodeWithIssues(
        test.language,
        test.difficulty,
        test.category,
        test.description
      );
      
      const duration = Date.now() - startTime;
      console.log(`✅ Generated in ${duration}ms (${(duration/1000).toFixed(1)}s)`);
      console.log(`📝 Code length: ${result.length} characters`);
      console.log('---');
      
    } catch (error) {
      const duration = Date.now() - startTime;
      console.log(`❌ Failed after ${duration}ms: ${error.message}`);
      console.log('---');
    }
  }
}

// Run the test
testAISpeed().catch(console.error);