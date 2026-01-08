"""
Chat Forms
"""

from django import forms
from .models import ChatRoom


class CreateRoomForm(forms.ModelForm):
    """Form for creating a chat room"""
    
    class Meta:
        model = ChatRoom
        fields = ('name', 'description', 'room_type', 'max_members')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Room name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Room description (optional)',
                'rows': 3
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2,
                'max': 1000
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data['name']
        if len(name) < 3:
            raise forms.ValidationError('Room name must be at least 3 characters.')
        return name


class InviteUserForm(forms.Form):
    """Form for inviting users to a room"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username to invite'
        })
    )
