# Test file for pre-commit hook verification
def test_function(
    x, y, z
):  # Missing spaces, long line that violates Black formatting rules and should be reformatted accordingly
    result = x + y + z
    return result
