def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "TOP"),
        html_link(f"{BASE_URL}/BsT/", "BsT"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""
