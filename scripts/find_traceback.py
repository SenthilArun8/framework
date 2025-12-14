try:
    with open('log.txt', 'r', encoding='utf-16') as f:
        content = f.read()
        idx = content.find("Traceback")
        if idx != -1:
            with open('trace.txt', 'w') as out:
                out.write(content[idx:idx+2000])
        else:
            print("No traceback found.")
except Exception as e:
    print(f"Error: {e}")
