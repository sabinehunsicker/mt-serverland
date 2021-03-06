"""
Project: MT Server Land prototype code
 Author: Christian Federmann <cfedermann@dfki.de>
"""
import logging
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from serverland.dashboard.models import TranslationRequest, WorkerServer
from serverland.dashboard.forms import TranslationRequestForm
from serverland.settings import LOG_LEVEL, LOG_HANDLER

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('dashboard.views')
LOGGER.addHandler(LOG_HANDLER)

@login_required
def dashboard(request):
    """
    Renders the MT Server Land dashboard for the current user.
    
    Does not yet work for anonymous users!
    """
    LOGGER.info('Rendering dashboard for user "{0}".'.format(
      request.user.username))
    
    ordered = TranslationRequest.objects.all().order_by('-created')
    requests = [r for r in ordered if not r.deleted]
    finished = [r for r in requests if r.is_ready()]
    invalid = [r for r in requests if not r.is_valid() and not r in finished]
    active = [r for r in requests if not r in finished and not r in invalid]
    
    dictionary = {'title': 'MT Server Land (prototype) -- Dashboard',
      'finished_requests': finished, 'active_requests': active,
      'invalid_requests': invalid}
    return render_to_response('dashboard/dashboard.html', dictionary,
      context_instance=RequestContext(request))

@login_required
def create(request):
    """
    Creates a new translation request for the current user.
    
    Does not yet work for anonymous users!
    """
    LOGGER.info('Rendering create request view for user "{0}".'.format(
      request.user.username))

    form = None
    
    if request.method == "POST":
        form = TranslationRequestForm(request.POST, request.FILES)
        
        if form.errors:
            LOGGER.info('Form validation errors: {0}'.format(
              ['{0}: {1}'.format(a, b[0]) for a, b in form.errors.items()]))
        
        if form.is_valid():
            LOGGER.info('Create request form is valid.')

            new = TranslationRequest()
            new.shortname = request.POST['shortname']
            new.worker = WorkerServer.objects.get(
              pk=int(request.POST['worker']))
            new.source_text = request.FILES['source_text']
            
            text = ''
            for chunk in request.FILES['source_text'].chunks():
                text += chunk
            
            new.request_id = new.start_translation(text)
            
            if not new.request_id:
                LOGGER.warning('Could not start translation request!')
                messages.add_message(request, messages.ERROR,
                  'Could not start translation request!')
                return HttpResponseRedirect('/dashboard/')
            
            new.owner = request.user
            new.save()
            
            messages.add_message(request, messages.SUCCESS,
              'Successfully started translation request.')
            return HttpResponseRedirect('/dashboard/')
        
    else:
        form = TranslationRequestForm()

    #from serverland.dashboard.models import WorkerServer
    #workers = WorkerServer.objects.all()
    #active_workers = [w for w in workers if w.is_alive()]
    
    dictionary = {'title': 'MT Server Land (prototype) -- Create translation',
      'form': form}
    return render_to_response('dashboard/create.html', dictionary,
      context_instance=RequestContext(request))

@login_required
def delete(request, request_id):
    """
    Deletes a translation request.
    """
    req = get_object_or_404(TranslationRequest, request_id=request_id)
    
    if req.owner != request.user:
        LOGGER.warning('Illegal delete request from user "{0}".'.format(
          request.user.username or "Anonymous"))
        
        return HttpResponseRedirect('/dashboard/')
    
    LOGGER.info('Deleting translation request "{0}" for user "{1}".'.format(
      request_id, request.user.username or "Anonymous"))
    req.delete_translation()
    
    messages.add_message(request, messages.SUCCESS, 'Successfully deleted' \
      ' request "{0}".'.format(req.shortname))
    return HttpResponseRedirect('/dashboard/')

@login_required
def result(request, request_id):
    """
    Returns the result of a translation request.
    """
    req = get_object_or_404(TranslationRequest, request_id=request_id)

    if req.owner != request.user:
        LOGGER.warning('Illegal result request from user "{0}".'.format(
          request.user.username or "Anonymous"))
        
        return HttpResponseRedirect('/dashboard/')

    LOGGER.info('Fetching request "{0}" for user "{1}".'.format(
      request_id, request.user.username or "Anonymous"))
    translation_result = req.fetch_translation()
    
    dictionary = {'title': 'MT Server Land (prototype) -- {0}'.format(
      req.shortname), 'request': req, 'result': translation_result}
    return render_to_response('dashboard/result.html', dictionary,
      context_instance=RequestContext(request))

@login_required
def download(request, request_id):
    """
    Downloads the result of a translation request.
    """
    req = get_object_or_404(TranslationRequest, request_id=request_id)

    if req.owner != request.user:
        LOGGER.warning('Illegal download request from user "{0}".'.format(
          request.user.username or "Anonymous"))
        
        return HttpResponseRedirect('/dashboard/')

    LOGGER.info('Downloading request "{0}" for user "{1}".'.format(
      request_id, request.user.username or "Anonymous"))
    response = HttpResponse(req.fetch_translation(), mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename={0}.txt'.format(
      req.shortname)
    return response