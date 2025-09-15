// Ollama Performance Configuration for DevFlow
module.exports = {
  // Model preferences (fastest to slowest)
  modelPreferences: [
    'gpt-oss:7b',      // Fastest - good for demos
    'gpt-oss:14b',     // Balanced
    'gpt-oss:20b',     // Standard
    'gpt-oss:32b'      // Highest quality but slowest
  ],
  
  // Speed-optimized parameters
  speedOptimized: {
    temperature: 0.3,    // Lower for more deterministic, faster responses
    top_p: 0.6,         // Reduced for faster sampling
    top_k: 15,          // Smaller for speed
    num_ctx: 3072,      // Balanced context
    num_predict: 250,   // Shorter responses
    num_thread: 8,      // Use available CPU threads
    repeat_penalty: 1.05
  },
  
  // Quality-optimized parameters (for final demo)
  qualityOptimized: {
    temperature: 0.4,
    top_p: 0.7,
    top_k: 40,
    num_ctx: 8192,      // Your suggested larger context
    num_predict: 400,
    num_thread: 8,
    repeat_penalty: 1.1
  },
  
  // Demo mode - ultra fast for live presentations
  demoMode: {
    temperature: 0.2,
    top_p: 0.5,
    top_k: 10,
    num_ctx: 2048,      // Minimal context for speed
    num_predict: 150,   // Very short responses
    num_thread: 8,
    repeat_penalty: 1.0
  }
};