def generate_html_table(names, max_seats):
    num_names = len(names)
    num_rows = -(-max_seats // 2) if max_seats > 0 else 1  # Calculate number of rows based on max_seats
    html_table = "<tbody>\n"
    
    for i in range(num_rows):
        html_table += "  <tr>\n"
        for j in range(2):
            index = i * 2 + j
            if index < num_names:
                html_table += f"    <td>{names[index]}</td>\n"
            else:
                html_table += f"    <td>---</td>\n"
        html_table += "  </tr>\n"
    
    html_table += "</tbody>"
    return html_table

# Example usage:
max_seats = 4
name_list = ['name 1','name 1','name 1','name 1','name 1']  # Empty list

html_table = generate_html_table(name_list, max_seats)
print(html_table)
