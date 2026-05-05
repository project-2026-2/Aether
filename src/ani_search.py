import requests

def get_anilist_data(query, variables):
    url = 'https://graphql.anilist.co'
    try:
        response = requests.post(url, json={'query': query, 'variables': variables})
        return response.json()
    except Exception:
        return None

def search_anime(name):
    query = '''
    query ($search: String) {
      Page (perPage: 10) { 
        media (search: $search, type: ANIME) {
          id
          title { romaji native }
          description
          coverImage { large }
          bannerImage
          genres
          averageScore
          episodes
          status
          startDate { year month }
        }
      }
    }
    '''
    return get_anilist_data(query, {'search': name})