import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from textwrap import wrap

import re
import spacy
from nltk.metrics.distance import edit_distance
from sklearn.feature_extraction.text import TfidfVectorizer

from bs4 import BeautifulSoup
from requests import get
import wikipedia
import lyricsgenius as genius

###############################################################################################################################
############################################################ ETAPE  ##########################################################
###############################################################################################################################

###############################################################################################################################
############################################################ ETAPE 2 ##########################################################
###############################################################################################################################

def find_title_in_wikipedia(title, pourcentage=0.3):
    words = ["(chanteur)", "(chanteuse)", "(groupe)", "(rappeur)", "(rappeuse)", "(musicien)", "(chanteur français)", "(france)", "(producteur)", "(artiste)", "(groupe de musique)"]

    wikipedia.set_lang("fr")
    results = wikipedia.search(title, results=10)
    distance = []
    if len(results) > 0:
        for element in results:
            if any((w in element.lower()) and (edit_distance(element.lower().split(" (")[0].strip(), title.lower().strip())/len(title) < pourcentage) for w in words):
                return element

            distance.append(edit_distance(title.lower().strip(), element.lower().strip()))

        return results[np.argmin(distance)] if min(distance)/len(title) < pourcentage else np.NaN


def wiki_birth(title):
    cols = ["Naissance", "Pays d'origine", "Origine", "Nationalité", "Pays", "Summary"]
    dic = {w : np.NaN for w in cols}

    if title is np.NaN:
        return dic

    url = f"https://fr.wikipedia.org/wiki/{title}"
    rq = get(url)

    if not rq.ok:
        return dic
    
    soup = BeautifulSoup(rq.text)
    tables = soup.findAll("table")

    for table in tables:
        trs = table.findAll("tr")

        for tr in trs:
            th = tr.find("th")

            if th is not None:
                for w in cols:
                    if w in th.text:
                        td = tr.find("td")
                        if td is not None:
                            dic[w] = td.text.strip().lower()

    wikipedia.set_lang("fr")
    try:
        summary = wikipedia.summary(title, sentences=1)
        dic["Summary"] = summary.lower().strip()
    except:
        pass

    return dic


def add_id(df : pd.DataFrame, cols : list, id_name : str):
    df_unique = df[cols].drop_duplicates(ignore_index=True)
    df_unique[id_name] = df_unique.index

    return df.merge(df_unique, on=cols, how="inner")

###############################################################################################################################
############################################################ ETAPE 3 ##########################################################
###############################################################################################################################

def pie_chart(df, col, title, na=True, legends=[], colors=["green", "red"], figsize=(3,3)):
    if na:
        df[col].isna().value_counts(normalize=True).round(2).plot.pie(autopct="%.2f%%", figsize=figsize, colors=colors)
    else:
        df[col].value_counts(normalize=True).round(2).plot.pie(autopct="%.2f%%", figsize=figsize, colors=colors)
    plt.title(title, color='white')
    plt.gcf().set_facecolor('black')
    plt.legend(legends, bbox_to_anchor=(1, 0.5))
    plt.show()

def category_count(cols, df, figsize=(40,7), top=10):
    length = []
    for col in cols:
        length.append(len(df[col].unique()))

    fig, ax = plt.subplots(1, len(cols)+1, figsize=figsize)

    sns.barplot(x=cols, y=length, ax=ax[0])
    ax[0].set_title("Nombre de valeurs différentes pour chaque colonne")

    for axi, col in zip(ax[1:], cols):
        df[col].value_counts().head(top)[::-1].plot.barh(ax=axi)
        axi.set(title=f"Top {top} de {col}", xlabel="Nombre d'occurence")
        axi.set_yticklabels(["\n".join(wrap(elem.get_text(), 10)) for elem in axi.get_yticklabels()])

###############################################################################################################################
############################################################ ETAPE 4 ##########################################################
###############################################################################################################################

def get_nationality(data_to_check, check_list):
    if data_to_check is np.NaN:
        return np.NaN
        
    for r in check_list:
        regex = r"([\d)()\], ]|^)"+ r.lower() + r"([.,\[) ]|$)"

        if not re.search(regex, data_to_check.lower()) is None:
            return r.lower()
    return np.NaN


#Permet de récupérer la localisation d'un artiste à partir de sa naissance ou sommaire wikipedia
def get_localisation(row, localisation):
    for r in localisation:
        regex = r"([\d)()\] ]|^)" + r.lower() + r"([.,\[) ]|$)"

        if (not re.search(regex, str(row["summary"]).lower()) is None) or (not re.search(regex, str(row["naissance"]).lower()) is None):
            return r.lower()
    return np.NaN

###############################################################################################################################
############################################################ ETAPE 5 ##########################################################
###############################################################################################################################

def find_lyrics(x):
    g = genius.Genius("19WnPxjd0b-zuJeynlxyOZ7UItqsAPQbVk3libvr4DsUGLgzyNjwp4jig6dMerlq")
    g.verbose = False
    try:
        song = g.search_song(title=x["music"], artist=x["artist"], get_full_info=False)
        return song.lyrics
    except:
        return np.NaN

###############################################################################################################################
############################################################ ETAPE 6 ##########################################################
###############################################################################################################################

def remove_translation(lyrics:str):
    start = lyrics.split(" lyrics")[0]
    isUpperNum = [k for k, l in enumerate(start) if l.isupper() or l.isnumeric()]
    idx = isUpperNum[-1]

    k = 2
    while lyrics[idx-1] in ["-", " ", ".", "(", "&", "/"] or lyrics[idx-1].isupper() or lyrics[idx-1].isnumeric():
        idx = isUpperNum[-k]
        k += 1
        
    return lyrics[idx:]

def check_good_lyrics_without_translation(lyrics, title, p=0.3):
    if lyrics is np.NaN:
        return False
    
    song_title_lyrics = lyrics.lower().split(" lyrics")[0]
    song_title_lyrics_without_parent = re.sub(r" [\(\[].*?[\)\]]", "", song_title_lyrics)
    distance_without = edit_distance(song_title_lyrics_without_parent, title.lower())
    distance = edit_distance(song_title_lyrics, title.lower())

    return distance/len(title) <= p or distance_without/len(title) <= p


def check_good_lyrics_with_translation(lyrics, title, p=0.3):
    if lyrics is np.NaN:
        return False

    song_title_lyrics = lyrics.lower().split(" lyrics")[0]
    song_title_lyrics = song_title_lyrics[-len(title):]
    distance = edit_distance(song_title_lyrics, title.lower())
    return distance/len(title) <= p


def remove_title_lyrics(lyrics:str):
    idx = re.search(" lyrics", lyrics.lower()).span()[1]
    return lyrics[idx:]


def remove_crochet(lyrics:str):
    lyrics = re.sub(r"[\(\[].*?[\)\]]", "", lyrics)
    lyrics = re.sub(r"\n", " ", lyrics)
    lyrics = re.sub(" +", " ", lyrics)
    return lyrics


def cleanning_lyrics(row):
    lyrics = row["lyrics"]
    title = row["music"]

    if lyrics is np.NaN:
        return np.NaN

    if "lyrics" in title:
        raise ValueError("Y'a le mot lyrics dans le titre")
        
    # On s'occupe des paroles qui ont des traductions
    if lyrics.lower().startswith("translation"):
        if not check_good_lyrics_with_translation(lyrics, title) and not check_good_lyrics_without_translation(remove_translation(lyrics), title):
            return np.NaN
        else:
            lyrics = remove_translation(lyrics)
    else:
        if not check_good_lyrics_without_translation(lyrics, title):
            return np.NaN

    # On met tous en minuscule
    lyrics = lyrics.lower()

    # On enleve le titre du debut
    lyrics = remove_title_lyrics(lyrics)
        
    # On enleve les crochets
    lyrics = remove_crochet(lyrics)

    # On enleve le 'embed' a la fin
    if lyrics.endswith("embed"):
        lyrics = lyrics[:-5]

    lyrics = lyrics.strip()

    return lyrics
###############################################################################################################################
############################################################ ETAPE 7 ##########################################################
###############################################################################################################################

def is_french(string, nlp):
    if string is np.NaN:
        return False

    doc = nlp(string)
    return doc.lang_ == "fr"

def lematization(lyrics : str, nlp : spacy.lang):
    lyrics_lemma = [token.lemma_ for token in nlp(lyrics) if not token.is_stop]
    return " ".join(lyrics_lemma)

def tfidf_mat(corpus : list):
    tfidf = TfidfVectorizer()
    mat = tfidf.fit_transform(corpus)
    return pd.DataFrame(mat.toarray(), columns=tfidf.get_feature_names_out())