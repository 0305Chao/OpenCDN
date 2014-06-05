#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# author : firefoxbug
# E-Mail : wanghuafire@gmail.com
# Blog   : www.firefoxbug.com

""" OpenCDN Purge module: purge cdn cache.

OpenCDN module instruction : 
	OCDN_PURGE

Purge API :
	http://node_ip:node_port/ocdn/purge/purge?token=node_token&domain=node_domain
"""

import sys
import os
import time
try:
	import json
except Exception, e:
	import simplejson as json

parent, bindir = os.path.split(os.path.dirname(os.path.abspath(sys.argv[0])))
if os.path.exists(os.path.join(parent, 'lib')):
	sys.path.insert(0, os.path.join(parent, 'lib'))

from OcdnQueue import Consumer
from OcdnQueue import Producer
from OcdnLogger import init_logger
from OcdnJob import JobManager

class Purge(Consumer):
	"""OpenCDN Domain cache Purge

	1. Register task module into Consumer
	"""
	def __init__(self, queue_ip='103.6.222.21', queue_port=4730):
		self.queue_ip = queue_ip
		self.queue_port = queue_port
		self.CURRENT_TASK_MODULE = 'OCDN_PURGE'
		self.logfile = os.path.join(parent,'logs','%s.log'%(self.CURRENT_TASK_MODULE))
		super(Purge, self).__init__(queue_ip, queue_port, logfile=self.logfile)
		self.logger = init_logger(logfile=self.logfile, logmodule=self.CURRENT_TASK_MODULE, stdout=True)

	def run(self):
		"""Register callback module and start a worker loop do tasks"""
		self.register_task_callback(self.CURRENT_TASK_MODULE, self.do_task)
		self.start_worker()

	def do_task(self, gearman_worker, job):
		"""run a task may cause 3 results

		1. task excuted failed
		2. task excuted success and the job fished
		3. task excuted success but the job unfished
		"""
		data = job.data
		current_job_json = json.loads(data)
		jobmanager = JobManager(current_job_json)
		if not jobmanager.check_job_json_is_ok() :
			self.logger.error('Parse job json failed.%s'%(job.data))
			return "False"

		# Get task and parameters to run
		task_name, task_args = jobmanager.get_current_task_to_run()

		# Run task
		if self.purge_node(task_args) == False:
			self.logger.error('TaskModule:%s do task failed. DATA:%s'%(self.CURRENT_TASK_MODULE, data))
			self.purge_node_failure(jobmanager)
			return "False"

		self.logger.info('TaskModule:%s: do task success'%(self.CURRENT_TASK_MODULE))
		# Job is over
		if jobmanager.is_job_finished():
			self.logger.info('TaskModule:%s: Job is finished'%(self.CURRENT_TASK_MODULE))
			self.purge_job_success()
			return "True"

		
		# Job still has tasks to dispatch
		next_task_json = jobmanager.set_next_task_to_run()
		if not next_task_json :
			self.logger.error('[FAILED] Job is unfished but no more task to do')
			return "False"
		self.put_task_into_queue(next_task_json['CurrentTask'], next_task_json)
		return "True"

	def purge_node(self, task_args):
		"""run task purge one node cache

		return False: job filed
		return True: job success
		"""
#		for instance in task_args:
#			print instance
		print '-'*20, 'do task ', '-'*20
		return True

	def purge_node_failure(self, jobmanager):
		"""do with purge one node cache failured, try to dispatch the task again."""
		next_task_json = jobmanager.try_run_current_task_again()
		if not next_task_json :
			error_msg = '[FAILED] TaskModule:%s Exceed MaxRunTimes, no more dispatch'%(self.CURRENT_TASK_MODULE)
			self.logger.error(error_msg)
		else :
			info_msg = 'TaskModule:%s. try to redo task. AlreadyRunTimes=%s'%(self.CURRENT_TASK_MODULE, next_task_json['RunTimesLimit']['AlreadyRunTimes'])
			self.logger.info(info_msg)
			self.put_task_into_queue(next_task_json['CurrentTask'], next_task_json)
		
		
	def purge_job_success(self):
		"""The purge job is excuted successfully"""
		pass

	def put_task_into_queue(self, queue_name, task_json):
		"""Put a new task json into task queue"""
		self.push_task(self.queue_ip, self.queue_port, str(queue_name), task_json)

if __name__ == '__main__':
	purge = Purge()
	purge.run()