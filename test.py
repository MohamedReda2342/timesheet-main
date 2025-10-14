from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

hashed = pwd.hash("admin123")
print("Hash:", hashed)
print("Verify:", pwd.verify("admin123", hashed))
