import qrcode

def generate_qr_code(link, output_file="qrcode.png"):
    """Generates a QR code for a given hyperlink and saves it as an image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    
    img = qr.make_image(fill="black", back_color="white")
    img.save(output_file)
    print(f"QR code saved as {output_file}")

if __name__ == "__main__":
    link = input("Enter the hyperlink: ")
    generate_qr_code(link)
