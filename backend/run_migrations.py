import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.absolute()
sys.path.append(str(backend_dir))

# Now run the Alembic CLI
if __name__ == "__main__":
    os.system(f"cd {backend_dir} && alembic revision --autogenerate -m 'Initial migration' && alembic upgrade head") 