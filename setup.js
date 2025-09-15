#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🚀 Setting up DevFlow - Code Review Training Platform');
console.log('');

// Function to run commands and handle errors
function runCommand(command, description) {
  console.log(`📦 ${description}...`);
  try {
    execSync(command, { stdio: 'inherit' });
    console.log(`✅ ${description} completed successfully`);
  } catch (error) {
    console.error(`❌ Error during ${description}:`, error.message);
    process.exit(1);
  }
  console.log('');
}

// Check if Node.js and npm are installed
try {
  execSync('node --version', { stdio: 'pipe' });
  execSync('npm --version', { stdio: 'pipe' });
  console.log('✅ Node.js and npm are installed');
} catch (error) {
  console.error('❌ Node.js and npm are required. Please install them first.');
  process.exit(1);
}

// Install root dependencies
runCommand('npm install', 'Installing root dependencies');

// Install server dependencies
runCommand('cd server && npm install', 'Installing server dependencies');

// Install client dependencies
runCommand('cd client && npm install', 'Installing client dependencies');

// Initialize database with seed data
console.log('🗄️  Initializing database with seed data...');
try {
  execSync('cd server && node seedData.js', { stdio: 'inherit' });
  console.log('✅ Database initialized successfully');
} catch (error) {
  console.error('❌ Error initializing database:', error.message);
  process.exit(1);
}

console.log('');
console.log('🎉 DevFlow setup completed successfully!');
console.log('');
console.log('To start the development servers:');
console.log('  npm run dev');
console.log('');
console.log('This will start:');
console.log('  - Backend API server on http://localhost:3001');
console.log('  - Frontend React app on http://localhost:3000');
console.log('');
console.log('🎯 Ready to showcase Kiro\'s development workflow!');
console.log('');
console.log('Key features to demonstrate:');
console.log('  ✨ Spec-driven development (.kiro/specs/)');
console.log('  🤖 Agent hooks for automation (.kiro/hooks/)');
console.log('  📋 Development guidelines (.kiro/steering/)');
console.log('  🎨 AI-assisted full-stack development');
console.log('  📊 Interactive code review training');
console.log('');