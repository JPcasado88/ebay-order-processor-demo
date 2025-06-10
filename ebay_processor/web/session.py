from flask_session.sessions import FileSystemSessionInterface

class PatchedFileSystemSessionInterface(FileSystemSessionInterface):
    """Extensión de FileSystemSessionInterface con limpieza automática de sesiones antiguas."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cleanup_old_sessions()
    
    def _cleanup_old_sessions(self):
        """Limpia sesiones antiguas al iniciar la aplicación."""
        import os
        import time
        from datetime import datetime, timedelta
        
        if not os.path.exists(self.cache_dir):
            return
            
        # Eliminar sesiones más antiguas que 24 horas
        cutoff = time.time() - (24 * 3600)
        for filename in os.listdir(self.cache_dir):
            if filename.startswith(self.key_prefix):
                path = os.path.join(self.cache_dir, filename)
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                    except OSError:
                        pass 