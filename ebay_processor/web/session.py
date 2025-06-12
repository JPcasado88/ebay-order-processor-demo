from flask_session.sessions import FileSystemSessionInterface

class PatchedFileSystemSessionInterface(FileSystemSessionInterface):
    """Extension of FileSystemSessionInterface with automatic cleanup of old sessions."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanup_old_sessions()
    
    def _cleanup_old_sessions(self):
        """Cleans up old sessions when starting the application."""
        import os
        import time
        from datetime import datetime, timedelta
        
        if not os.path.exists(self.cache_dir):
            return
            
        # Delete sessions older than 24 hours
        cutoff = time.time() - (24 * 3600)
        for filename in os.listdir(self.cache_dir):
            if filename.startswith(self.key_prefix):
                path = os.path.join(self.cache_dir, filename)
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                    except OSError:
                        pass 