try:
    with open('log.txt', 'r', encoding='utf-16') as f:
        lines = f.readlines()
        print("".join(lines[-100:]))
except Exception as e:
    print(f"Error: {e}")
