#!/usr/bin/env python3
"""
LinkedIn Engagement Extractor - Parse likes/comments from scraped content

Compact utility for batch processing.
"""

import re


def extract_engagement(content: str) -> dict:
    """
    Extract engagement metrics from scraped LinkedIn content.
    
    Handles various formats:
    - "512 reactions" or "[512]"
    - "45 Comments" or "45 comments"
    
    Returns:
        dict: {'likes': int, 'comments': int}
    """
    likes = 0
    comments = 0
    
    # Pattern 1: [512] format
    likes_match = re.search(r'\[(\d+)\]', content)
    if likes_match:
        likes = int(likes_match.group(1))
    
    # Pattern 2: "512 reactions" format
    if not likes:
        reactions_match = re.search(r'(\d+)\s+reactions?', content, re.IGNORECASE)
        if reactions_match:
            likes = int(reactions_match.group(1))
    
    # Pattern 3: "45 Comments" format
    comments_match = re.search(r'(\d+)\s+comments?', content, re.IGNORECASE)
    if comments_match:
        comments = int(comments_match.group(1))
    
    return {'likes': likes, 'comments': comments}


def extract_main_text(content: str) -> str:
    """
    Extract main post text from scraped LinkedIn content.
    
    Removes:
    - LinkedIn UI elements
    - Navigation text
    - Sign-in prompts
    """
    # Remove common LinkedIn UI text
    noise_patterns = [
        'Report this post',
        'Like Comment Share',
        'To view or add a comment',
        'Welcome back',
        'Sign in',
        'Join for free',
        'New to LinkedIn',
        'Email or phone',
        'Password',
        'Forgot password',
        'LinkedIn ©',
        'About Accessibility',
        'User Agreement',
        'Privacy Policy',
        'Cookie Policy',
        'Copyright Policy',
        'Brand Policy',
    ]
    
    text = content
    for pattern in noise_patterns:
        text = text.replace(pattern, '')
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    return text


if __name__ == '__main__':
    # Test
    test_content = '''
    John (JR) Renaldi's Post
    
    Finally pushed an LLM to the limits and it went completely bonker!
    
    [54] 22 Comments
    
    Like Comment Share
    '''
    
    engagement = extract_engagement(test_content)
    text = extract_main_text(test_content)
    
    print(f"Engagement: {engagement}")
    print(f"Text: {text[:100]}...")
