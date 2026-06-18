"""Fix conftest.py to add table creation"""

with open('conftest.py', 'r') as f:
    content = f.read()

# Add table creation after session creation
old_text = """    # Create session bound to the connection
    session = Session(bind=connection)
    
    # Begin nested transaction (savepoint)"""

new_text = """    # Create session bound to the connection
    session = Session(bind=connection)
    
    # Create tables if they don't exist (first time setup)
    Base.metadata.create_all(bind=engine)
    
    # Begin nested transaction (savepoint)"""

content = content.replace(old_text, new_text)

with open('conftest.py', 'w') as f:
    f.write(content)

print("✅ Fixed conftest.py - added table creation")
