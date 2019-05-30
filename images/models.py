from django.db import models

# Create your models here.
class Page(models.Model):
    typeid = models.IntegerField()
    sendtime=models.DateField()
    title=models.CharField(max_length=200)
    firstimg=models.CharField(max_length=200)
    tagid=models.CharField(max_length=200)

class Image(models.Model):
    pageid=models.IntegerField()
    imageurl=models.URLField()

class Type(models.Model):
    type=models.CharField(max_length=200)

class Tag(models.Model):
    tag = models.CharField(max_length=200)


