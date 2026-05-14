FROM python:3.14

# copy the entire project source tree
COPY . /project
WORKDIR /project

# install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# NOTE: this does not work with gunicorn - it does not serve static files
# collect static files into the STATIC_ROOT directory
# see https://docs.djangoproject.com/en/5.2/howto/static-files/
#RUN python manage.py collectstatic
# NOTE: when combined with the VOLUME instruction below, changes in the files
#       from the RUN command would not affect the existing volume

# create a directory for staticfiles (will be mounted as a volume)
#RUN mkdir /project/staticfiles
#VOLUME /project/staticfiles

# the MEDIA_ROOT directory exists in the project but must be set as a volume
# (the content from git will initialize the container volume when it is created)
#VOLUME /project/media

# Publish a port on which the application should be accessible from the host (and other containers)
EXPOSE 8000

# collect static files, perform database migrations and run the webserver
#CMD python manage.py collectstatic --no-input --clear && python manage.py migrate && gunicorn main.wsgi --bind 0.0.0.0:8000
CMD python manage.py migrate && python manage.py runserver 0.0.0.0:8000
