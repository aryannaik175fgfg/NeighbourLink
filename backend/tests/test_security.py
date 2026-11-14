from app.core.security import hash_password, verify_password


def test_argon2_hash_and_verify():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed)
    assert not verify_password("wrong", hashed)
