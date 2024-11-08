# portal/views.py
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from .services.api_service import AstroAPIService
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import os
from django.conf import settings
from django.urls import reverse
import time
import base64
from .utils import save_base64_file  # Add this import
import tempfile
from datetime import datetime
from django.utils.dateformat import format as date_format
from django.utils import formats


INTERVENTION_STEPS = [
    'security_checklist',
    'photo_upload',  # current step
    'photos_after',
    'comment',
    # ... other steps
]

class LoginView(View):
    template_name = 'portal/login.html'

    def get(self, request):
        if 'token' in request.session:
            return redirect('interventions')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')

        api_service = AstroAPIService()
        response = api_service.login(email, password)

        if response and response.get('success'):
            request.session['token'] = response['token']
            request.session['user'] = {
                'uid': response['uid'],
                'email': response['email'],
                'firstname': response['firstname'],
                'lastname': response['lastname']
            }
            return redirect('interventions')
        else:
            messages.error(request, response.get('message', 'Login failed'))
            return render(request, self.template_name)


# views.py


class InterventionListView(View):
    template_name = 'portal/interventions/list.html'

    def get(self, request):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        # Initialize today
        today = datetime.now().strftime('%Y-%m-%d')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        interventions = api_service.get_interventions(token, user_uid, page=1)

        if interventions:
            # Convert date strings and sort interventions
            grouped_interventions = {}
            today_interventions = []

            for intervention in interventions:
                try:
                    # Convert date from 'dd/mm/yyyy' to datetime object
                    date_obj = datetime.strptime(intervention['date_time'], '%d/%m/%Y')
                    date_key = date_obj  # Keep as datetime object for template formatting

                    # Add intervention to appropriate group
                    if date_obj.strftime('%Y-%m-%d') == today:
                        today_interventions.append(intervention)
                    else:
                        if date_key not in grouped_interventions:
                            grouped_interventions[date_key] = []
                        grouped_interventions[date_key].append(intervention)

                except ValueError as e:
                    print(f"Error parsing date: {e}")
                    continue

            # Sort dates
            sorted_dates = sorted(grouped_interventions.keys())
            sorted_interventions = {}

            # Add today's interventions if they exist
            if today_interventions:
                sorted_interventions['today'] = today_interventions

            # Add other dates
            for date in sorted_dates:
                sorted_interventions[date] = grouped_interventions[date]

        else:
            sorted_interventions = {}

        return render(request, self.template_name, {
            'grouped_interventions': sorted_interventions,
            'today': today
        })

# portal/views.py
class InterventionDetailView(View):
    template_name = 'portal/interventions/detail.html'

    def get(self, request, intervention_id):
        print(f"DEBUG: Accessing detail view for intervention {intervention_id}")

        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get all interventions and find the specific one
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            # Find the specific intervention
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                return render(request, self.template_name, {
                    'intervention': intervention
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')


# portal/views.py
@method_decorator(csrf_exempt, name='dispatch')
class InterventionUpdateStatusView(View):
    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'}, status=401)

        try:
            # No need to parse request body anymore since we're always setting to 'en_cours'
            api_service = AstroAPIService()
            result = api_service.update_intervention_status(
                request.session['token'],
                intervention_id,
                'en_cours'  # Status is hardcoded since we're always setting to 'en_cours'
            )

            if result:
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'Failed to update status'})

        except Exception as e:
            print(f"Error updating status: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class SecurityChecklistView(View):
    template_name = 'portal/interventions/security_checklist.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get all interventions and find the specific one
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                # Check if status_uid is 5 (En cours)
                if intervention.get('status_uid') == '5':
                    return render(request, self.template_name, {
                        'intervention': intervention
                    })
                else:
                    messages.error(request, 'Cette intervention n\'est pas en cours')
                    return redirect('intervention_detail', intervention_id=intervention_id)

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')
        current_step_index = INTERVENTION_STEPS.index('security_checklist')
        next_step = INTERVENTION_STEPS[current_step_index + 1]
        next_url = reverse(next_step, kwargs={'intervention_id': intervention_id})

        return render(request, self.template_name, {
            'intervention': intervention,
            'next_url': next_url
        })

@method_decorator(csrf_exempt, name='dispatch')
class PhotoUploadView(View):
    template_name = 'portal/interventions/photo_upload.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                print(f"DEBUG: Intervention images_before: {intervention.get('images_before')}")  # Debug print
                return render(request, self.template_name, {
                    'intervention': intervention,
                    'intervention_images': intervention.get('images_before', ''),
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')

    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'code': '0', 'message': 'error2'})

        if 'file' not in request.FILES:
            return JsonResponse({'code': '2', 'message': 'no record'})

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # First, get current intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)
        intervention = next(
            (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if not intervention:
            return JsonResponse({'code': '0', 'message': 'Intervention not found'})

        # Upload file
        response = api_service.upload_media(
            token,
            request.FILES['file'],
            intervention_id,
            intervention
        )

        if response:
            return JsonResponse(response)

        return JsonResponse({'code': '0', 'message': 'error1'})


@method_decorator(csrf_exempt, name='dispatch')
class PhotosAfterView(View):
    template_name = 'portal/interventions/photos_after.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get fresh intervention data
        all_interventions = api_service.get_interventions(token, user_uid, page=1)

        if all_interventions:
            intervention = next(
                (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
                None
            )

            if intervention:
                print(f"DEBUG: Intervention images_after: {intervention.get('images_after')}")  # Debug print

                # Get next step URL
                current_step_index = INTERVENTION_STEPS.index('photos_after')
                next_step = INTERVENTION_STEPS[current_step_index + 1] if current_step_index + 1 < len(
                    INTERVENTION_STEPS) else None
                next_url = reverse(next_step, kwargs={'intervention_id': intervention_id}) if next_step else None

                return render(request, self.template_name, {
                    'intervention': intervention,
                    'intervention_images': intervention.get('images_after', ''),
                    # Pass images_after instead of images_before
                    'next_url': next_url
                })

        messages.error(request, 'Intervention non trouvée')
        return redirect('interventions')


# views.py
class CommentView(View):
    template_name = 'portal/interventions/comment.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session or 'user' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get intervention details
        all_interventions = api_service.get_interventions(token, user_uid, page=1)
        intervention = next(
            (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            return render(request, self.template_name, {
                'intervention': intervention
            })

        return redirect('interventions')


# views.py
class QualityControlView(View):
    template_name = 'portal/interventions/quality_control.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        intervention = next(
            (i for i in api_service.get_interventions(token, user_uid, page=1)
             if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            return render(request, self.template_name, {
                'intervention': intervention,
                'quality_items': [
                    'Ranger les outils',
                    'Nettoyer le chantier',
                    'Mise en pression des appareils sanitaires',
                    'Vérifier le gaz'
                ]
            })

        return redirect('interventions')


# views.py
class SignatureView(View):
    template_name = 'portal/interventions/signature.html'

    def get(self, request, intervention_id):
        if 'token' not in request.session:
            return redirect('login')

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        intervention = next(
            (i for i in api_service.get_interventions(token, user_uid, page=1)
             if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            return render(request, self.template_name, {
                'intervention': intervention
            })

        return redirect('interventions')


class GetInterventionFilesView(View):
    def get(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        api_service = AstroAPIService()
        token = request.session['token']
        user_uid = request.session['user']['uid']

        # Get intervention
        all_interventions = api_service.get_interventions(token, user_uid, page=1)
        intervention = next(
            (i for i in all_interventions if str(i.get('uid')) == str(intervention_id)),
            None
        )

        if intervention:
            # Get files from the files_urls field
            files = []
            if intervention.get('files_urls'):
                files = [url.strip() for url in intervention['files_urls'].split(';') if url.strip()]

            return JsonResponse({
                'success': True,
                'files': files
            })

        return JsonResponse({
            'success': False,
            'message': 'Intervention not found'
        })


# views.py
# views.py
@method_decorator(csrf_exempt, name='dispatch')
class FinishInterventionView(View):
    def post(self, request, intervention_id):
        if 'token' not in request.session:
            return JsonResponse({'success': False, 'message': 'Not authenticated'})

        try:
            data = json.loads(request.body)
            quality = data.get('quality', '')
            signature_data = data.get('signature', '')
            images_before = data.get('images_before', '')
            images_after = data.get('images_after', '')
            comment = data.get('comments', '')

            api_service = AstroAPIService()
            token = request.session['token']

            # Save signature using add_media API
            signature_path = ''
            if signature_data:
                try:
                    # Convert base64 to file-like object
                    if ',' in signature_data:
                        signature_data = signature_data.split(',')[1]

                    import base64
                    import io
                    from django.core.files.uploadedfile import InMemoryUploadedFile

                    # Decode base64 to bytes
                    signature_bytes = base64.b64decode(signature_data)

                    # Create a file-like object
                    signature_file = io.BytesIO(signature_bytes)

                    # Create an InMemoryUploadedFile with proper content type
                    filename = f'signature_{int(time.time())}.png'
                    file = InMemoryUploadedFile(
                        signature_file,
                        None,  # field_name
                        filename,  # file name
                        'image/png',  # content type
                        len(signature_bytes),  # size
                        None  # charset
                    )

                    # Upload using add_media
                    upload_response = api_service.upload_media(token, file)

                    if upload_response and upload_response.get('code') == '1':
                        signature_path = upload_response.get('file_path', '')
                    else:
                        print("Signature upload failed:", upload_response)  # Debug print
                        return JsonResponse({'success': False, 'message': 'Error uploading signature'})

                except Exception as e:
                    print(f"Error processing signature: {str(e)}")
                    return JsonResponse({'success': False, 'message': 'Error processing signature'})

            # Send everything to set_intervention_recap
            response = api_service.set_intervention_recap(
                token=token,
                intervention_id=intervention_id,
                security='1;1;1',
                quality=quality,
                images_before=images_before,
                images_after=images_after,
                comments=comment,
                signature=signature_path,
                items='',
                status_uid=4
            )

            if response and response.get('code') == 1:
                return JsonResponse({'success': True})

            return JsonResponse({'success': False, 'message': 'Failed to update intervention'})

        except Exception as e:
            print(f"Finish intervention error: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)})

class LogoutView(View):
    def get(self, request):
        request.session.flush()
        return redirect('login')