from app.local_llm import LocalLLM


def test_local_llm_generates_response():
    llm = LocalLLM()

    response = llm.generate(
        question="What is the return policy?",
        context=(
            "Customers can return eligible items within 30 days "
            "of delivery."
        ),
    )

    assert isinstance(response, str)
    assert len(response.strip()) > 0