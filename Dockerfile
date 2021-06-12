FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mv example.config.py config.py

EXPOSE 8080

CMD [ "python", "./main.py" ]