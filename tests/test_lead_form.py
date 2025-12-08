from backend.server import is_lead_form_message


def test_is_lead_form_message_positive():
    text = """What is your Child's age ?: 16 months to 3 years
What is your primary goal for your child's development?: Early learning & brain development
Full name: Nikita Mahajan
Phone number: 098661 18236
Email: neemanikita3101@gmail.com
City: Bangalore"""
    assert is_lead_form_message(text) is True


def test_is_lead_form_message_negative():
    text = "Hi, I'm interested in your program"
    assert is_lead_form_message(text) is False
