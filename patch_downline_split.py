with open("models.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = "def get_downline_count(user_id: str) -> int:"
assert anchor in content, "get_downline_count anchor not found"

new_func = '''def get_downline_count_by_side(user_id: str):
    from collections import deque

    def count_subtree(root_id):
        if not root_id:
            return 0
        count = 0
        queue = deque([root_id])
        with get_db_cursor() as c:
            while queue:
                current_id = queue.popleft()
                count += 1
                c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (current_id,))
                node = c.fetchone()
                if node:
                    if node["left_child"]:
                        queue.append(node["left_child"])
                    if node["right_child"]:
                        queue.append(node["right_child"])
        return count

    with get_db_cursor() as c:
        c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return 0, 0
    left_count = count_subtree(row["left_child"])
    right_count = count_subtree(row["right_child"])
    return left_count, right_count


'''
content = content.replace(anchor, new_func + anchor, 1)

with open("models.py", "w", encoding="utf-8") as f:
    f.write(content)

print("models.py: get_downline_count_by_side added")
