# Use Selenium Webdriver to backup/restore customsearch.ai instance(s)

Currently there is no way to export/import any configured Bing Custom Search instances that have been created at
`customsearch.ai`.

These scripts attempt to achieve that, by using Selenium Webdriver to crawl the search instance configuration pages, and
export the data to file. The exported data is then able to be used to recreate the configuration elsewhere (eg. under a
development account), by automating the steps a user would take when creating configuration, using the backed up data.

See the `Usage` section below for details of how to use the script.

Other approaches to achieve the same outcome might include:

- Figure out and use API calls the Angular app executes, reformatting/storing/using the returned JSON data
- Other headless browser options

## Choices

The reason to use Selenium Webdriver is because the `customsearch.ai` pages are very Javascript heavy. Other crawling
technologies exist, but the ability to crawl over pages with large amounts of script makes them a more complicated
option.

To use Webdriver, in this case with Firefox, you need to have the browser installed, and also have the relevant
'driver' binary downloaded/available.

    https://github.com/mozilla/geckodriver

The path to the relevant 'driver' is required to be known in the python script(s). You can either place the binaries on
the somewhere already in `$PATH`, or pass a path when calling the webdriver.

An example of passing the path to the driver:

    browser = webdriver.Firefox(executable_path=r'/Users/alex/Downloads/geckodriver')

The `/usr/local/bin` directory is part of the `$PATH`, so download the driver(s), un-tar it and copy it to the
`/usr/local/bin` directory. **These script(s) rely on this method**.

## Requirements

As we want to persist Bing Custom Search instance configuration in file(s), the data should be structured, and so will
be stored as JSON.

One development option is to develop in a Python virtualenv, to keep all our dependencies together, not overwriting any
system modules etc. Another option  would be to use a Docker image with all required Python modules contained within.

These scripts were developed in a virtualenv (when using `Fish` shell):

    cd ~/Work/scraping
    virtualenv customsearch.ai
    cd customsearch.ai
    source bin/activate.fish
    pip install selenium
    pip install ...
    ... python commands ...
    python main.py <user.name>@example.org <password> [--restore_file customsearch.ai.XXXXXXXX_YYYYYY_ZZZZZZ.json]
    deactivate

In the above commands:

- the `source` command will differ depending on your shell. The example above is for use with the `Fish` shell
- the `python` command will use the virtualenv's version of python, until you run deactivate
- `python` version used during development, 3.6

### Usage

To backup search instances:

    python main.py <user.name>@example.org <password>

A file named in the format `customsearch.ai.XXXXXXXX_YYYYYY_ZZZZZZ.json` will be created in the same directory as
`main.py`.

To restore them in/with a different account:

    python main.py <other.user.name>@example.org <password> --restore_file customsearch.ai.XXXXXXXX_YYYYYY_ZZZZZZ.json

### Backup(/export) scenario

The general outline of what needs to be done to backup the search instance config is as follows (always starting as an
anonymous, logged out, user):

    Go to www.customsearch.ai
    Sign in
    Iterate through all listed search instance configuration(s), and for each one...
    Navigate through all pages of links in each 'Active, 'Blocked' and 'Pinned' tabs, grabbing data
    Structure search instance data and save to file

### Restore(/import) from backup scenario

When restoring, we will not overwrite any existing configuration with the same name. If an instance already
exists with the same name as is being restored, the restored instance will be renamed.

The general outline of what needs to be done to restore from a previously backed up file is as follows:

    Go to www.customsearch.ai
    Sign in
    Load the specified exported file
    Iterate through the instance configuration(s) in the file, and for each one...
    Rename the instance being resstored, if one already exists with the same name
    Iterate through the 'Active, 'Blocked' and 'Pinned' data in the file, recreating instance configuration

Restored instances names will be prefixed with `(I)` to indicate they were inported. Eg. `My instance` will be named
`(I)My instance` after restore.

### Known issues/limitations

- Sometimes, when logging in the user, the password form takes longer than the alloted wait of 3 seconds to show,
and the process stalls. Just re-run the process. Could be solved by making the wait longer, is one not particularly good
way/a workaround. Converting to Page Objects should solve things a different way.

- Although the 'Date created' for the backed up data is recorded, it cannot be used when restoring to a new instance as
that field is not editable.

- Only the ability to restore all instances in a file exists. You can restore all, then manually remove those not
required.

- Only tested with Webdriver Firefox (59). Other versions should work, as *should* Chrome with Chromedriver

### Documentation links

    https://virtualenv.pypa.io/en/stable/
    https://docs.seleniumhq.org
    http://selenium-python.readthedocs.io
    https://github.com/mozilla/geckodriver
