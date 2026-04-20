import setuptools

setuptools.setup(
    name="prompting",
    version="0.0.1",
    author="Claudiu Adam",
    author_email="adam.claudiu00@gmail.com",
    description="Meteorological data processing and LLM prompting",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.12',
)