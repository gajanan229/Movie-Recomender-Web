import pandas as pd


def get_recommendations(ids, cosine_sim, df1):
    rec_list = []

    # Iterate over each movie id to get the recommendations for each movie
    for id in ids:
        # Get the index of the movie that matches the title
        idx = df1.index[df1['id'] == id][0]

        # Get the pairwsie similarity scores of all movies with that movie
        sim_scores = list(enumerate(cosine_sim[idx]))

        # Sort the movies based on the similarity scores
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Get the scores of the 30 most similar movies
        sim_scores = sim_scores[1:30]
        # Get the movie indices
        movie_indices = [i[0] for i in sim_scores]

        # Return the top 10 most similar movies with an average rating of over 5 from over 50 users
        df_return = df1.loc[movie_indices]
        df_return = df_return[df_return['vote_average'] >= 5]
        df_return = df_return[df_return['vote_count'] >= 50][1:11]
        rec_list.append(df_return)

    inter_rec = []
    leng = len(rec_list)

    if leng == 1:
        return rec_list[0]['id'].tolist()
    # if more than one movie find intersection between recommendations
    else:
        for i, rec in enumerate(rec_list):
            if i != leng - 1:
                for rec2 in rec_list[i + 1:]:
                    inter_rec.append(pd.merge(rec, rec2, how='inner', on=['adult', 'belongs_to_collection', 'budget', 'genres', 'homepage', 'id', 'imdb_id', 'original_language', 'original_title', 'overview', 'popularity', 'poster_path', 'production_companies', 'production_countries', 'release_date', 'revenue', 'runtime', 'spoken_languages', 'status', 'tagline', 'title', 'video', 'vote_average', 'vote_count', 'cast', 'crew', 'keywords']))

    # based on number of user's movies set variables
    val1 = 2
    if leng == 2:
        pos_ver = 0
    elif leng == 3:
        val = 3
        pos_ver = 3
        for i, rec in enumerate(rec_list[1:]):
            if i == 0:
                # if three movies finding the intersection between all movies
                inter_rec.append(pd.merge(inter_rec[0], rec, how='outer',
                                          on=['adult', 'belongs_to_collection', 'budget', 'genres', 'homepage', 'id',
                                              'imdb_id', 'original_language', 'original_title', 'overview',
                                              'popularity', 'poster_path', 'production_companies',
                                              'production_countries', 'release_date', 'revenue', 'runtime',
                                              'spoken_languages', 'status', 'tagline', 'title', 'video',
                                              'vote_average', 'vote_count', 'cast', 'crew', 'keywords']))
            else:
                inter_rec[pos_ver] = pd.merge(inter_rec[0], rec, how='outer', on=['adult', 'belongs_to_collection', 'budget', 'genres', 'homepage','id', 'imdb_id', 'original_language', 'original_title', 'overview', 'popularity', 'poster_path', 'production_companies', 'production_countries', 'release_date', 'revenue', 'runtime', 'spoken_languages', 'status', 'tagline', 'title', 'video', 'vote_average', 'vote_count', 'cast', 'crew', 'keywords'])

    # if there are more than 9 movies return the first 10 movies sorted by rating
    if len(inter_rec[pos_ver]) > 9:
        return inter_rec[pos_ver].sort_values(by="vote_average")[:10].reset_index()['id'].tolist()
    # if less than 10 add movies from alternating list.
    else:
        i = 0
        while inter_rec[pos_ver].shape[0] < 10:
            inter_rec[pos_ver] = pd.concat(
                [inter_rec[pos_ver], rec_list[i % val1].loc[[rec_list[i % val1].index[i // val1]]]])
            inter_rec[pos_ver].drop_duplicates(inplace=True)
            # return the list if no more movies left in the original list 'inter_rec'
            if i // val1 > 9:
                return inter_rec[pos_ver].reset_index()['id'].tolist()
            i = i + 1
        return inter_rec[pos_ver].reset_index()['id'].tolist()



