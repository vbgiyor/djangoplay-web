from django.http import Http404
from django.shortcuts import redirect
from django.views import View


class IssueRootRedirectView(View):

    """
    Redirect / → /issues/ only for issues subdomain.
    """

    def get(self, request):
        host = request.get_host()

        if not host.startswith("issues."):
            raise Http404()

        return redirect("issues:list")
