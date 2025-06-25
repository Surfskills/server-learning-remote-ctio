# courses/context_processors.py
def content_availability(request):
    def is_content_available(content_object):
        if not request.user.is_authenticated:
            return False
        return content_object.course.is_content_available_for(request.user, content_object)
    
    return {
        'is_content_available': is_content_available
    }