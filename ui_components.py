import streamlit as st


def inject_custom_theme():
    """Injects clean fonts and standard UI enhancements without changing the page structure."""
    st.markdown(
        """
        <style>
            @import url('https://googleapis.com');
            
            html, body, [data-testid="stAppViewContainer"] {
                font-family: 'Inter', sans-serif !important;
            }
            
            /* Clean look for input boxes */
            .stTextInput input {
                border-radius: 8px !important;
                padding: 12px !important;
            }
            
            /* Rounded corners for history tracking and stats */
            div[data-testid="stExpander"] {
                border-radius: 10px !important;
            }
            .stMetric {
                background: #f8f9fa;
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #eaeaea;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_login_header():
    """Generates standard typography for the account login area."""
    st.markdown(
        "<h2 style='text-align: center; margin-bottom: 0px;'>🤖 Sujoy's Chat Bot</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #666; font-size: 14px;'>Please login/register first</p>",
        unsafe_allow_html=True,
    )
