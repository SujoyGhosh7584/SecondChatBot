import streamlit as st


def inject_custom_theme():
    """Injects clean fonts and standard UI enhancements adapting smoothly to light/dark themes."""
    st.markdown(
        """
        <style>
            /* 1. Correct Google Fonts Link for Inter */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
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
            
            /* 2. Theme-aware Metric Boxes using Streamlit CSS Variables */
            .stMetric {
                background: var(--background-color, #f8f9fa);
                background-color: rgba(128, 128, 128, 0.06); /* Subtle cross-theme overlay tint */
                padding: 12px;
                border-radius: 10px;
                border: 1px solid rgba(128, 128, 128, 0.15);
            }
        </style>
    """,
        unsafe_allow_html=True,
    )


def render_login_header():
    """Generates standard typography for the account login area with adaptive subtext color."""
    st.markdown(
        "<h2 style='text-align: center; margin-bottom: 0px;'>🤖 Sujoy's Chat Bot</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <p style='text-align: center; color: var(--text-color, #666); opacity: 0.7; font-size: 14px; margin-top: 4px;'>
            Please login/register first
        </p>
        """,
        unsafe_allow_html=True,
    )
