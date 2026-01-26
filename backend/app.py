import streamlit as st
# Import the main function from your other script
from video_ranker_multimodal import get_ranked_videos, TEXT_WEIGHT, VISUAL_WEIGHT

# --- Page Configuration ---
st.set_page_config(
    page_title="Multimodal Video Search",
    page_icon="🎬",
    layout="wide"
)

# --- Page Title ---
st.title("🎬 Multimodal Focus-Filtering System")
st.write("This app ranks videos based on your 'focus' using both text and visuals.")

# --- Search Bar ---
user_intent = st.text_input(
    "What would you like to focus on?", 
    "I want to study linear algebra"
)

# --- Rank and Display Results ---
if user_intent:
    # Get the ranked list from our imported function
    ranked_list = get_ranked_videos(user_intent)
    
    # Our filtration rule: Only show videos with a score > 0.10
    MIN_SCORE = 0.10 
    filtered_list = [
        item for item in ranked_list if item['final_score'] > MIN_SCORE
    ]
    
    if not filtered_list:
        st.warning("No relevant videos found. Try a different query.")
    else:
        st.subheader("Ranked Video Results:")
        
        # Display results in columns
        for item in filtered_list:
            st.markdown("---") # Horizontal line
            
            col1, col2 = st.columns([1, 4]) # 1 part image, 4 parts text
            
            with col1:
                # Show the thumbnail
                st.image(item['thumbnail_path'], width=150)
            
            with col2:
                # Show the title and scores
                st.subheader(f"{item['title']}")
                st.write(f"**Final Score: {item['final_score']:.2f}**")
                
                with st.expander("Show Score Details"):
                    st.progress(item['final_score'])
                    st.write(f"Text Score: {item['text_score']:.2f} (Weight: {TEXT_WEIGHT*100}%)")
                    st.write(f"Visual Score: {item['visual_score']:.2f} (Weight: {VISUAL_WEIGHT*100}%)")