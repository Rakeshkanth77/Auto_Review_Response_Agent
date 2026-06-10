import streamlit as st
import os
from dotenv import load_dotenv
from products import PRODUCTS
from review_agent import run_review_flow
import datetime

# Load env variables
load_dotenv(override=True)

# Resolve API Key & model settings globally for deployment
api_key_input = ""
try:
    if "GROQ_API_KEY" in st.secrets:
        api_key_input = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not api_key_input:
    api_key_input = os.getenv("GROQ_API_KEY") or ""

model_name = "openai/gpt-oss-120b"
base_url = "https://api.groq.com/openai/v1"

# Set page config
st.set_page_config(
    page_title="Aura Threadworks | AI Customer Support Agent POC",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (CSS Injection)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .brand-title {
        font-size: 3rem;
        font-weight: 700;
        letter-spacing: 2px;
        background: linear-gradient(90deg, #1A1A2E 0%, #16213E 50%, #0F3460 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    .brand-subtitle {
        font-size: 1.1rem;
        font-weight: 300;
        color: #555;
        letter-spacing: 1px;
        margin-top: 0px;
        margin-bottom: 2rem;
    }
    
    .product-card {
        border-radius: 12px;
        background-color: #ffffff;
        padding: 16px;
        border: 1px solid #EAEAEA;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        transition: all 0.3s ease;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.05);
        border-color: #16213E;
    }
    
    .product-price {
        font-weight: 600;
        font-size: 1.25rem;
        color: #1A1A2E;
    }
    
    .review-box {
        border-left: 4px solid #16213E;
        background-color: #F7F9FB;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
    }
    
    .agent-response-card {
        background: linear-gradient(135deg, #16213E 0%, #0F3460 100%);
        color: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 8px 16px rgba(15, 52, 96, 0.2);
        margin-top: 15px;
    }
    
    /* Stepper Styling for LangGraph Flow */
    .stepper-container {
        display: flex;
        flex-direction: column;
        margin: 20px 0;
    }
    
    .step-item {
        display: flex;
        align-items: flex-start;
        margin-bottom: 20px;
        position: relative;
    }
    
    .step-item:not(:last-child)::after {
        content: '';
        position: absolute;
        left: 20px;
        top: 40px;
        bottom: -20px;
        width: 2px;
        background-color: #E2E8F0;
        z-index: 1;
    }
    
    .step-icon {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background-color: #EDF2F7;
        border: 2px solid #CBD5E0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        z-index: 2;
        transition: all 0.3s;
    }
    
    .step-icon.active {
        background-color: #10B981;
        border-color: #059669;
        color: white;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
    }
    
    .step-icon.active-alt {
        background-color: #3B82F6;
        border-color: #2563EB;
        color: white;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
    }

    .step-icon.active-neutral {
        background-color: #6B7280;
        border-color: #4B5563;
        color: white;
    }

    .step-content {
        margin-left: 20px;
        padding-top: 4px;
    }
    
    .step-title {
        font-weight: 600;
        font-size: 1.1rem;
        color: #2D3748;
    }
    
    .step-desc {
        font-size: 0.9rem;
        color: #718096;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Define preset template reviews for testing
TEST_REVIEWS = {
    "Positive Review": {
        "text": "The Elysian Wool Trench is magnificent. The fabric is thick and warm, and it fits true to size. I've received so many compliments already!",
        "rating": 5
    },
    "Negative (UX/UI - Misleading Photo)": {
        "text": "The color of the Sherpa Denim Jacket in the product pictures looks like a vintage dark blue indigo, but in person it is a very washed-out light blue. The photo is misleading, though the coat itself fits okay.",
        "rating": 3
    },
    "Negative (Bug/Defect - Loose Stitching)": {
        "text": "Extremely upset. My Pleated Linen Shorts came with loose stitching on the waistband. The hem completely unraveled after the first wash, and I can't wear them anymore. Quality is not what I expected for this price.",
        "rating": 1
    },
    "Negative (Urgent Support - Broken Zipper)": {
        "text": "The zipper on this Arctic Puffer Coat broke the very first time I zipped it up! I'm heading out on a ski trip tomorrow morning and have no winter coat now. Please respond immediately with a replacement or refund!!",
        "rating": 1
    }
}

# Sidebar - Configuration
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=200&auto=format&fit=crop&q=80", width=120)
    st.markdown("### Aura Threadworks POC")
    st.caption("AI-Powered E-commerce & Support Agent")
    st.divider()
    

    st.divider()
    st.markdown("#### Tech Stack & Architecture")
    st.markdown("""
    - **Frontend**: Streamlit (Premium UI)
    - **Agent Framework**: LangGraph
    - **Chains**: LangChain + Pydantic
    - **Inference**: Groq API
    """)
    st.caption("Developed as a Portfolio Proof-of-Concept")

# Main Title Header
st.markdown('<p class="brand-title">AURA THREADWORKS</p>', unsafe_allow_html=True)
st.markdown('<p class="brand-subtitle">Curated Sustainable Luxury & Smart Customer Care</p>', unsafe_allow_html=True)

# Session state initialization
if 'selected_product' not in st.session_state:
    st.session_state.selected_product = None
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "shop"
if 'review_text_input' not in st.session_state:
    st.session_state.review_text_input = ""
if 'review_rating_input' not in st.session_state:
    st.session_state.review_rating_input = 5
if 'agent_result' not in st.session_state:
    st.session_state.agent_result = None

# Callback for back to shop
def back_to_shop():
    st.session_state.selected_product = None
    st.session_state.active_tab = "shop"
    st.session_state.agent_result = None

# Shop Tab
if st.session_state.selected_product is None:
    st.markdown("### Sustainable Collection")
    
    # Filter & Search controls
    col_search, col_filter = st.columns([2, 3])
    
    with col_search:
        search_query = st.text_input("Search catalog...", placeholder="Search linen, wool, jacket...", label_visibility="collapsed")
        
    with col_filter:
        categories = ["All Products", "Outerwear", "Tops", "Bottoms", "Accessories & Loungewear"]
        selected_category = st.pills("Category", categories, default="All Products", label_visibility="collapsed")
        
    # Filter logic
    filtered_products = PRODUCTS
    
    # Filter by category
    if selected_category != "All Products":
        filtered_products = [p for p in filtered_products if p["category"] == selected_category]
        
    # Filter by search query
    if search_query:
        filtered_products = [
            p for p in filtered_products 
            if search_query.lower() in p["name"].lower() or search_query.lower() in p["description"].lower()
        ]
        
    # Grid display
    st.divider()
    if not filtered_products:
        st.info("No products found matching your criteria.")
    else:
        # Display 3 products per row
        row_size = 3
        for i in range(0, len(filtered_products), row_size):
            cols = st.columns(row_size)
            for j in range(row_size):
                if i + j < len(filtered_products):
                    product = filtered_products[i+j]
                    with cols[j]:
                        # Product card container
                        st.image(product["image"], use_container_width=True)
                        st.markdown(f"**{product['name']}**")
                        st.markdown(f"<span style='color: #718096; font-size: 0.9rem;'>{product['category']}</span>", unsafe_allow_html=True)
                        
                        # Star rating
                        rating_stars = "★" * int(product["rating"]) + "☆" * (5 - int(product["rating"]))
                        st.markdown(f"<span style='color: #F59E0B;'>{rating_stars}</span> ({product['rating']})", unsafe_allow_html=True)
                        
                        # Price and details button
                        col_price, col_btn = st.columns([1, 1])
                        with col_price:
                            st.markdown(f"<p class='product-price'>${product['price']:.2f}</p>", unsafe_allow_html=True)
                        with col_btn:
                            if st.button("Details & Review", key=f"details_{product['id']}", use_container_width=True):
                                st.session_state.selected_product = product
                                st.rerun()
                                
# Product Details & Agent Testing Tab
else:
    product = st.session_state.selected_product
    
    st.button("← Back to Shop", on_click=back_to_shop)
    st.divider()
    
    col_prod_info, col_reviews = st.columns([2, 3])
    
    # Left Column: Product Information
    with col_prod_info:
        st.image(product["image"], use_container_width=True)
        st.markdown(f"## {product['name']}")
        st.markdown(f"**Category:** {product['category']}")
        
        rating_stars = "★" * int(product["rating"]) + "☆" * (5 - int(product["rating"]))
        st.markdown(f"### <span style='color: #F59E0B;'>{rating_stars}</span> {product['rating']} / 5", unsafe_allow_html=True)
        
        st.markdown(f"### ${product['price']:.2f}")
        st.markdown(product["description"])
        
    # Right Column: Reviews and Agent trigger
    with col_reviews:
        st.markdown("### Customer Reviews")
        
        # Display existing reviews
        for rev in product["reviews"]:
            stars = "★" * rev["rating"] + "☆" * (5 - rev["rating"])
            st.markdown(f"""
            <div class="review-box">
                <strong>{rev['user']}</strong> <span style="color: #F59E0B; margin-left: 8px;">{stars}</span>
                <span style="color: #718096; font-size: 0.8rem; float: right;">{rev['date']}</span>
                <p style="margin-top: 6px; font-size: 0.95rem;">{rev['comment']}</p>
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        st.markdown("### Test the Review Response Agent")
        st.caption("Write a review or select a preset template below. The LangGraph agent will process the review, classify sentiment, diagnose issues, and craft an automated response.")
        
        # Preset template buttons
        st.markdown("**Auto-fill Test Templates:**")
        preset_cols = st.columns(4)
        for idx, (label, template) in enumerate(TEST_REVIEWS.items()):
            with preset_cols[idx]:
                if st.button(label, key=f"tpl_{idx}", use_container_width=True):
                    st.session_state.review_text_input = template["text"]
                    st.session_state.review_rating_input = template["rating"]
                    st.session_state.agent_result = None
                    st.rerun()

        # Review Inputs
        review_rating = st.slider("Rating", min_value=1, max_value=5, value=st.session_state.review_rating_input, key="rating_slider")
        review_text = st.text_area("Review Comment", value=st.session_state.review_text_input, height=120, placeholder="Type your experience with this product...")
        
        # Trigger review agent
        if st.button("Submit Review & Trigger AI Support Response", type="primary", use_container_width=True):
            if not api_key_input:
                st.error("Groq API Key is not configured. Please add it to your environment variables or Streamlit secrets.")
            elif not review_text.strip():
                st.warning("Please type a review before submitting.")
            else:
                with st.spinner("LangGraph agent is analyzing and executing workflow..."):
                    try:
                        # Call the review responder logic
                        result = run_review_flow(
                            review_text=review_text,
                            api_key=api_key_input,
                            model_name=model_name,
                            base_url=base_url
                        )
                        st.session_state.agent_result = result
                        st.session_state.review_text_input = review_text # retain
                    except Exception as e:
                        st.error(f"Error executing agent workflow: {e}")
                        
        # Display Agent outputs if available
        if st.session_state.agent_result:
            res = st.session_state.agent_result
            
            st.divider()
            st.markdown("### LangGraph Response Output")
            
            # Show final generated response
            st.markdown(f"""
            <div class="agent-response-card">
                <h5 style="margin-top:0px; color:#F7F9FB; letter-spacing:1px;">AUTOMATED SUPPORT REPLY:</h5>
                <p style="font-size: 1rem; line-height: 1.6; margin-bottom: 0px; white-space: pre-line;">{res['response']}</p>
            </div>
            """, unsafe_allow_html=True)
            

