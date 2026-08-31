document.addEventListener('DOMContentLoaded', function() {
    const bodMeetingField = document.getElementById('id_bod_meeting');
    const agendaField = document.getElementById('id_agenda');

    if (bodMeetingField) {
        bodMeetingField.addEventListener('change', function() {
            const meetingId = bodMeetingField.value;

            agendaField.innerHTML = '<option value="">Select Agenda</option>';

            if (meetingId) {
                fetch(`/get_agendas/?meeting_id=${meetingId}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.agendas) {
                            data.agendas.forEach(agenda => {
                                const option = document.createElement('option');
                                option.value = agenda.id;
                                option.textContent = agenda.title;
                                agendaField.appendChild(option);
                            });
                        } else {
                            console.error('Error:', data.error);
                        }
                    })
                    .catch(error => console.error('Error fetching agendas:', error));
            }
        });
    }
});
