use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

/// Manages cleanup of shared resources
pub struct ResourceManager {
    shutdown_initiated: Arc<AtomicBool>,
}

impl ResourceManager {
    pub fn new() -> Self {
        Self {
            shutdown_initiated: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Initiates shutdown of shared resources
    pub fn shutdown(&self) {
        self.shutdown_initiated.store(true, Ordering::SeqCst);
    }

    /// Checks if shutdown has been initiated
    pub fn is_shutting_down(&self) -> bool {
        self.shutdown_initiated.load(Ordering::SeqCst)
    }
}

impl Default for ResourceManager {
    fn default() -> Self {
        Self::new()
    }
}

impl Drop for ResourceManager {
    fn drop(&mut self) {
        // Ensure cleanup is performed
        if !self.is_shutting_down() {
            self.shutdown();
        }
    }
}