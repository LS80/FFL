import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage 
from email.utils import COMMASPACE, formatdate
from email import encoders
from os.path import basename

class HTMLEmail(object):
	def __init__(self, to, sender, name, bcc=None, reply_to=None):
		assert type(to)==list
		self.to = to
		self.sender = sender
		self.name = name
		if bcc is not None:
			self.bcc = [bcc]
		else:
			self.bcc = []
		self.reply_to = reply_to
	
	def send(self, subject, html, smtp_server, images=[], zipfile=None):

		msg = MIMEMultipart()
		msg['From'] = '{0} <{1}>'.format(self.name, self.sender)
		msg['To'] = COMMASPACE.join(self.to)
		msg['Date'] = formatdate(localtime=True)
		msg['Subject'] = subject
		if self.reply_to is not None:
			msg['Reply-To'] = self.reply_to
	
		msg.attach(MIMEText(html.encode('utf-8'), 'html', 'utf-8'))
		
		for i, image in enumerate(images):
			img = MIMEImage(image.read())
			img.add_header('Content-ID', '<image{0}>'.format(i+1))
			msg.attach(img)
		
		if zipfile:
			zip = MIMEBase('application', 'zip')
			zip.set_payload(zipfile.read())
			encoders.encode_base64(zip)
			zip.add_header('Content-Disposition', 'attachment; filename=%s' % basename(zipfile))
			msg.attach(zip)

		smtp = smtplib.SMTP(smtp_server)
		smtp.sendmail(self.sender, set(self.to+self.bcc), msg.as_string())
		smtp.close()
		
if __name__ == '__main__':
	em = HTMLEmail(['test@lee-smith.me.uk'],
				   "lee@lee-smith.me.uk", "FFL",
				   bcc="bcc@lee-smith.me.uk", reply_to="reply@lee-smith.me.uk")
	em.send('Testing', '<h1>Testing</h1><br><img height="500px" width="700px" src="cid:image1">',
			'localhost', images=['test.png'])
	