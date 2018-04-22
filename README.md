## About ##
This script is for finding a good apartment on [wg-gesucht](https://www.wg-gesucht.de). It can take the commute time to multiple places in the city into account and provides other, more fine grained filters, than the website normally enables. It writes everything into a google spreadsheet and gives you a desktop notification when a new apartment was found. Already found apartments that get pushed up in the search history by the poster don't get added to the spreadsheet again.

This saves you time looking at apartments that have suboptimal location and that you already applied to, making the whole experience less of a chore.

## Installing ##
1. Clone the repository
2. Import the module into python via `pip install --user -e /PATH/TO/REPO/`


## Usage ##

1. Adjust the search settings and locations in `bot.py`
2. Set up gmaps developer api access
3. Add gmaps api keys to your environment variables or to `bot.py` directly
4. Add your `credentials.json` from the gmaps developer page
5. Adjust and run `trigger.sh` (optionally add it to a cronjob) 
