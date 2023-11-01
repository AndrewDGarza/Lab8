import bcrypt 

# example password 
password = 'passwordabc'

# converting password to array of bytes 
bytes = password.encode('utf-8') 

# generating the salt 
salt = bcrypt.gensalt() 

print(salt)

# Hashing the password 
hash = bcrypt.hashpw(bytes, salt) 

# Taking user entered password 
userPassword = 'passwordabc'

# encoding user password 
userBytes = userPassword.encode('utf-8') 

# checking password 
result = bcrypt.checkpw(userBytes, hash) 

print(result)
