import os

# Create necessary directories
directories = [
    'uploads',
    'shards',
]

for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")
    else:
        print(f"Directory already exists: {directory}")

print("\nAll required directories are ready!")
