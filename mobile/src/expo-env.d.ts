/// <reference types="expo/types" />

// Expo environment variable declarations
declare var process: {
  env: Record<string, string | undefined>;
};
