import os
import re
from playwright.sync_api import Playwright, sync_playwright, expect
from time import sleep
import streamlit as st
from datetime import datetime
import json
import pandas as pd

FOLDER_PREFIX = "5-web/cache"
COURSE_SELECTOR= "#fssearchresults > article.searchresult.search-courseresult > div > div.cols.noindent > span.text.detail-code.margin--tiny.text--semibold.text--big > strong"
TITLE_SELECTOR = "#fssearchresults > article.searchresult.search-courseresult > div > div.cols.noindent > span.text.detail-title.margin--tiny.text--semibold.text--big > strong"
CREDIT_SELECTOR = "#fssearchresults > article.searchresult.search-courseresult > div > div.cols.noindent > span.text.detail-hours_html.margin--tiny.text--semibold.text--big > strong"
DESCRIPTION_SELECTOR = "#fssearchresults > article.searchresult.search-courseresult > div > div:nth-child(5) > div"

def extract(playwright: Playwright, course: str, force: bool = False) -> str:
    '''
    Extract from course catalog course code `course and return the page in the cache
    as a filename.

    example: extract("MAT 221") returns "cache/MAT_221.html"
    '''
    coursefile = f"{FOLDER_PREFIX}/{course.replace(' ', '_')}.html"
    if not force:
        if os.path.exists(coursefile):
            print(f"Cache hit for {course}, returning {coursefile}")
            return coursefile # cache hit.

    # cache miss, we need to scrape the course description
    print(f"Cache miss for {course}, scraping the course description")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://coursecatalog.syracuse.edu/")
    page.get_by_role("textbox", name="Search catalog").click()
    page.get_by_role("textbox", name="Search catalog").fill(course)
    page.get_by_role("textbox", name="Search catalog").press("Enter")
    page.wait_for_selector(COURSE_SELECTOR)
    with open(coursefile, 'w') as f:
        f.write(page.content())

    return coursefile

def transform(playwright: Playwright, course_file: str, force: bool = False) -> dict:
    '''
    Read page from cache as `course_file` and extract the course information as a dictionary.
    We assume `course_file` exists and is a valid HTML file.

    example: transform("cache/MAT_221.html") returns
    {
        'course': 'MAT 221',
        'title' : ' Statistics for the Social Sciences',
        'credits': 3,
        'description': 'This course covers ...',
        'date': '2021-01-01'
    }
    '''
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"file:///workspace/{course_file}")
    # Parse the HTML and extract the course information
    course = page.query_selector(COURSE_SELECTOR).inner_text()
    title = page.query_selector(TITLE_SELECTOR).inner_text()
    credits = page.query_selector(CREDIT_SELECTOR).inner_text()
    description = page.query_selector(DESCRIPTION_SELECTOR).inner_text()
    course_info = {
        'course': course,
        'title': title,
        'credits': credits,
        'description': description,
        'date': datetime.now().strftime("%Y-%m-%d")
    }
    return course_info

def load(course_info: dict, course_list: list[dict], force: bool = False) -> list[dict]:
    '''
    Load course information from `course_info` into a list of dictionaries.

    example: load({'course': 'MAT 221', 'title' : ' Statistics for the Social Sciences', 'credits': 3, 'description': 'This course covers ...', 'date': '2021-01-01'}) returns
    [
        {
            'course': 'MAT 221',
            'title' : ' Statistics for the Social Sciences',
            'credits': 3,
            'description': 'This course covers ...',
            'date': '2021-01-01'
        }
    ]
    '''
    if not force:
        for item in course_list:
            if item['course'] == course_info['course']:
                return course_list # cache hit, return the list

    # cache miss, we need to add the course information to the list
    course_list.append(course_info)
    return course_list

def save(course_list: list[dict], filename: str = "courses.json",) -> None:
    '''
    Save course information from `course_list` into a JSON file.

    example: save([{'course': 'MAT 221', 'title' : ' Statistics for the Social Sciences', 'credits': 3, 'description': 'This course covers ...', 'date': '2021-01-01'}]) saves the list to courses.json
    '''
    with open(filename, 'w') as f:
        json.dump(course_list, f, indent=4)

def read(filename: str = "courses.json") -> list[dict]:
    '''
    Load course information from a JSON file.

    example: load("courses.json") returns
    [
        {
            'course': 'MAT 221',
            'title' : ' Statistics for the Social Sciences',
            'credits': 3,
            'description': 'This course covers ...',
            'date': '2021-01-01'
        }
    ]
    '''
    if not os.path.exists(filename):
        return []
    with open(filename, 'r') as f:
        course_list = json.load(f)
    return course_list


if __name__ == "__main__":
    course_list = read()
    with sync_playwright() as playwright:
        courses = ["MAT 221", "MAT 222", "IST 101"]
        for course in courses:
            course_file = extract(playwright, course, force=False)
            course_info = transform(playwright, course_file, force=False)
            course_list = load(course_info, course_list, force=False)
            print("Size of course list:", len(course_list))
            save(course_list)
            
        df = pd.json_normalize(course_list)
        print(df)