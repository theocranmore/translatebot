#!translatebot/bin/python

from PIL import Image
import pytesseract
import time
import praw
import urllib.request
import csv
import os
from time import sleep
import signal
import sys
from imgurpython import ImgurClient
from collections import OrderedDict
from imgurpython import ImgurClient
import urllib.parse
import io
from newspaper import Article
from google.cloud import translate
import six
import subprocess

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/theo/.config/gcloud/application_default_credentials.json"

subreddit_following = 'scottishtranslatebot'
words_list = "/home/theo/bin/scot/scottish_words.txt"

r = praw.Reddit(client_id='',
        client_secret='',
        redirect_uri='http://127.0.0.1:65010/'
                     'authorize_callback',
        user_agent='Translate Bot by /u/themusicalduck',
        username='ScottishTranslateBot',
        password='')

                                                    
imgur_id = ''                                       
                                                                                                                                        
imgur_secret = ''          


working_dir = "/home/theo/bin/scot/"
images_dir = "/home/theo/bin/scot/images/"
post_limit = 500

def save_data():
    
    print("saving")

    with open (working_dir + 'comments.csv', "w") as f:
        write_it = csv.writer(f)
        write_it.writerows(comments_done)

    with open (working_dir + 'submissions.csv', "w") as f:
        write_it = csv.writer(f)
        write_it.writerows(submissions_done)
    
    

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    save_data()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

def find_words(result):
    print(result)


    comment = ""
    comment+=translator.translate(result, lang_from='', lang_to='en')

    print(comment)
    return comment

def article_analysis(url):

    article = Article(url)
    print(url)
    article.download()
    article.parse()

    return translate_text('en', article.text[:10240])

def do_analysis(file_path):

    result = pytesseract.image_to_string(Image.open(file_path))
    print (result)

    return translate_text('en', result[:10240])

def make_post(submission, comment, count):
    files_list = None
    imgur_urls = None
    target_url = submission.url
    hosts = [ "imgur.com", "reddituploads.com", "i.redd.it", "reddit.com", "twimg.com", "itsosticky.com", "express.de", "20minutes.fr", "wikipedia.org" ]
    article_hosts = [ "express.de", "20minutes.fr", "wikipedia.org" ]
    message = ""
    if any(x in target_url for x in hosts):

        try:

            file_name = target_url.replace("/", "")
            file_path = images_dir + file_name
            
            if "imgur.com" in target_url:
                attempts = 0
                while True:

                    print("imgur link detected")
                    files_list = []
                    imgur_code = urllib.parse.urlparse(target_url)
                    imgur_code = imgur_code[2].rpartition('/')
                    print (imgur_code)
                    imgur_code = imgur_code[-1]
                    imgur_code = imgur_code.split('.', 1)[0]
                    print(imgur_code)
                    try:
    
                        imgur_client = ImgurClient(imgur_id, imgur_secret)                      
                        try:
                            imgur_urls = imgur_client.get_album_images(imgur_code)
                        except:
                            imgur_url = imgur_client.get_image(imgur_code)
    
                        if imgur_urls != None:
                            for idx, val in enumerate(imgur_urls):
                                url = val.link
                                print(url)
                                urllib.request.urlretrieve(url, file_path + str(idx))
                                files_list.append(file_path + str(idx))
                                if idx > 9:
                                    print("too many images, breaking")
                                    break
                                            
                            for i in files_list:
                                print(i)
                                message = message + do_analysis(i)
                        else:
                            urllib.request.urlretrieve(imgur_url.link, file_path)
                            message = do_analysis(file_path)
                            os.remove(file_path)

                        break
                    except Exception as e:
                        print("Exception:", e)
                        message = ""
                        attempts += 1
                        sleep(1)
                        if attempts > 4:
                            make_comment("Imgur is borked, sorry.", comment, submission, count)
                            return


            elif "reddit.com" in target_url:

                message = translate_text('en', submission.selftext)

            elif any(x in target_url for x in article_hosts):
                message = article_analysis(target_url)

            else:

                urllib.request.urlretrieve(submission.url, file_path)
                message = do_analysis(file_path)
                os.remove(file_path)

            if files_list != None:
                for i in files_list:
                    os.remove(i)
            #print (comment)
            if message not in (None, ""): 
                
                message = "Best guess for a translation of the words in this communication:\n\n" + message
                make_comment(message, comment, submission, count)
            else:
                print("COMMENT EMPTY")
                make_comment("Couldn't find any words in this communication!", comment, submission, count)

        except Exception as e:
             print("couldn't do analysis:", e)
             make_comment("Something broke! Sorry!", comment, submission, count)

    else:
        make_comment("Unnaproved host", comment, submission, count)

def make_comment(message, comment, submission, count):

    comments_done.append([comment.id])
    message = "\n\n".join(list(OrderedDict.fromkeys(message.split("\n\n"))))
    print(message)
    comment.reply(message)
    print(comment.id)

    if count != None:
        found = False
        for s in submissions_done:
            if comment.submission.id in s[0]:
                    s[1] = str(count)
                    found = True
        if found == False:
            submissions_done.append([submission.id, str(count)])

def translate_text(target, text):
    """Translates text into the target language.
    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """

    translate_client = translate.Client()

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    # Text can also be a sequence of strings, in which case this method
    # will return a sequence of results for each text.
    result = translate_client.translate(
        text, target_language=target)

    print(u'Text: {}'.format(result['input']))
    print(u'Translation: {}'.format(result['translatedText']))
    print(u'Detected source language: {}'.format(result['detectedSourceLanguage']))


def comments_stream():
    while True:

        summons = ['!translatebot', '!scottishtranslatebot']
        subreddit = r.subreddit(subreddit_following)
        generator = subreddit.stream.comments()

        for comment in generator:
            print(comment.body)
            # for comment in r.subreddit('moetron').comments(limit=10):

            is_done = False
            found = False

            if comment.body.lower() == summons[0].lower() and comment.author != 'ScottishTranslateBot':
                for i in comments_done:
                    if comment.id in i[0]:
                        print(comment.id, "comment already replied to")
                        is_done = True
                        found = True

                if is_done == False:
                    for s in submissions_done:
                        if comment.submission.id in s[0]:
                            print("Submission", comment.submission.id, "has been commented on", s[1], "times")
                            found = True
                            count = int(s[1])
                            if count < post_limit:
                                print("continuing")
                                count = count + 1
                                break
                            else:
                                is_done = True
                                break

                if found == False:
                    count = 1

                if is_done == False:
                    print("Attempting to post")
                    make_post(comment.submission, comment, count)

                    save_data()

        sleep(10)

def main(argv):

    global comments_done
    global submissions_done
    global comments_reader
    global submissions_reader

    with open(working_dir + 'comments.csv') as f:
        comments_reader = csv.reader(f)
        comments_done = list(comments_reader)
    
    with open(working_dir + 'submissions.csv') as f:
        submissions_reader = csv.reader(f)
        submissions_done = list(submissions_reader)
    
        comments_stream()

if __name__ == '__main__':
    main(sys.argv)
