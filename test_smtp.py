# test_smtp.py
import smtplib

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login('hizeetech@gmail.com', 'lrtkpzaqhwwowmcy')
        print("SMTP Connection Successful! (SSL)")
except Exception as e:
    print(f"Error: {e}")