jQuery(document).ready(function($) {
    // Registration form submission
    $('#wpai-registration-form').on('submit', function(e) {
        e.preventDefault();

        const $btn = $('#wpai-register-btn');
        const $spinner = $('.spinner');
        const $result = $('#wpai-result');

        // Disable button and show spinner
        $btn.prop('disabled', true);
        $spinner.addClass('is-active');
        $result.hide();

        $.ajax({
            url: wpaiConnector.ajax_url,
            type: 'POST',
            data: {
                action: 'wpai_register_site',
                nonce: wpaiConnector.nonce,
                api_key: $('#wpai-api-key').val(),
                site_name: $('#wpai-site-name').val(),
                wp_username: $('#wpai-username').val(),
            },
            success: function(response) {
                if (response.success) {
                    $result
                        .removeClass('notice-error')
                        .addClass('notice-success')
                        .html('<p><strong>' + wpaiConnector.i18n.success + '</strong> ' + response.data.message + '</p>')
                        .show();

                    // Reload page after 2 seconds to show connected state
                    setTimeout(function() {
                        location.reload();
                    }, 2000);
                } else {
                    $result
                        .removeClass('notice-success')
                        .addClass('notice-error')
                        .html('<p><strong>' + wpaiConnector.i18n.error + '</strong> ' + response.data.message + '</p>')
                        .show();

                    $btn.prop('disabled', false);
                }
            },
            error: function(xhr, status, error) {
                $result
                    .removeClass('notice-success')
                    .addClass('notice-error')
                    .html('<p><strong>' + wpaiConnector.i18n.error + '</strong> Network error. Please check your connection and try again.</p>')
                    .show();

                $btn.prop('disabled', false);
            },
            complete: function() {
                $spinner.removeClass('is-active');
            }
        });
    });

    // Disconnect button
    $('#wpai-disconnect').on('click', function() {
        if (!confirm('Are you sure you want to disconnect this site from WP-AI? This will revoke access and remove the application password.')) {
            return;
        }

        const $btn = $(this);
        $btn.prop('disabled', true).text('Disconnecting...');

        $.ajax({
            url: wpaiConnector.ajax_url,
            type: 'POST',
            data: {
                action: 'wpai_disconnect_site',
                nonce: wpaiConnector.nonce,
            },
            success: function(response) {
                if (response.success) {
                    alert(response.data.message);
                    location.reload();
                } else {
                    alert('Error: ' + response.data.message);
                    $btn.prop('disabled', false).text('Disconnect from WP-AI');
                }
            },
            error: function() {
                alert('Network error. Please try again.');
                $btn.prop('disabled', false).text('Disconnect from WP-AI');
            }
        });
    });

    // Toggle API key visibility
    let showingKey = false;
    $('#wpai-api-key').after('<button type="button" class="button button-small" id="wpai-toggle-key" style="margin-left: 5px;">Show</button>');

    $('#wpai-toggle-key').on('click', function() {
        showingKey = !showingKey;
        $('#wpai-api-key').attr('type', showingKey ? 'text' : 'password');
        $(this).text(showingKey ? 'Hide' : 'Show');
    });
});
